import os
import json
import pickle
import time
import numpy as np
import matplotlib.pyplot as plt

from ai2thor.controller import Controller
from ai2thor.platform import Linux64, CloudRendering

# from simulation.actions import get_action_classes
# from simulation.success_checker import check_task_success
# from simulation.change_injector import ChangeInjector

from actions import get_action_classes
from plan_success_checker import check_task_success
# from change_injector import ChangeInjector

import imageio, glob, os, numpy as np, PIL

def make_video_from_frames(records_dir, output_fname="plan_execution.mp4", fps=4):
    img_dir = os.path.join(records_dir, "ego_img")
    pngs = sorted(glob.glob(f"{img_dir}/step_*.png"),
                  key=lambda p: int(os.path.splitext(os.path.basename(p))[0].split("_")[-1]))
    if not pngs:
        print("No frames to make video.")
        return
    out_path = os.path.join(records_dir, output_fname)
    with imageio.get_writer(out_path, fps=fps) as writer:
        for p in pngs:
            img = PIL.Image.open(p).convert("RGB")
            writer.append_data(np.array(img))
    print(f"Saved video: {out_path}")

class Thor:
    def __init__(self, task_context, scenario_idx, records_dir):
        self.controller = None
        # self.change_injector = None
        self.counter = 0
        self.task_context = task_context
        self.scenario_idx = scenario_idx
        self.records_dir = records_dir
        self.log_archive = {}
        self.action_space = get_action_classes() # Close, Open, PickUp, PlaceOn, PlaceIn
        self.init_env()

    def init_env(self):            
        # Controller initialization
        self.controller = Controller(
            agentMode="default",
            massThreshold=None,
            scene=self.task_context["scene"],
            visibilityDistance=1.5,
            gridSize=0.05,
            renderDepthImage=False,
            renderInstanceSegmentation=False,
            width=1280,
            height=720,
            fieldOfView=90,
            platform=CloudRendering, # Use Linux64 for local rendering
            headless=False,
            snapGrid=False
        )
        self.controller.step(action="DisableTemperatureDecay")
        self.controller.step(action="Done")

        # Object initialization
        object_poses = []
        for object_init_state in self.task_context["objects_init_state"]:
            object_poses.append(
                {
                    "objectName": object_init_state["objectName"],
                    "position": object_init_state["position"],
                    "rotation": object_init_state["rotation"],
                }
            )            
        self.controller.step(action="SetObjectPoses", objectPoses=object_poses)
        self.controller.step(action="Done")

        for object_init_state in self.task_context["objects_init_state"]:
            for property in object_init_state.get("property"):
                # TODO: Require other properties?
                if property == 'dirty':
                    self.controller.step(
                        action="DirtyObject",
                        objectId=self.get_objectByName(object_init_state["objectName"])["objectId"],                    
                        forceAction=True
                    )
                elif property == 'open':
                    self.controller.step(
                        action="OpenObject",
                        objectId=self.get_objectByName(object_init_state["objectName"])["objectId"],                    
                        forceAction=True
                    )
        self.controller.step(action="Done")

        reachable_positions = self.controller.step(action="GetReachablePositions").metadata["actionReturn"]

        # Agent initialization
        self.controller.step(
            action="Teleport",
            position=self.task_context['robot_init_state']['position'],
            rotation=self.task_context['robot_init_state']['rotation'],
            horizon=self.task_context['robot_init_state']['horizon'],
            standing=True,
        )

        self.controller.last_event.metadata['errorMessage']

        self.controller.step(action="Done")

        # Change Injector initialization
        # self.change_injector = ChangeInjector(thor=self, task_context=self.task_context, scenario_idx=self.scenario_idx)

        # Save initial state and scene
        self.log(success=True, message="init")
        self.save_data()


    @property
    def is_hand_empty(self) -> bool:
        return self.agent_state["isHolding"] is None

    @property
    def agent_state(self):
        """
        {
            cameraHorizon: float,
            position: dict[str, float],
            rotation: dict[str, float],
            isStanding: True,
            isHolding: [object_metadata, None]
        }
        """
        event = self.controller.last_event
        agent_state = event.metadata["agent"]
        agent_state["isHolding"] = None

        for object_state in self.objects_state:
            if object_state["pickupable"] and object_state["isPickedUp"]:
                agent_state["isHolding"] = object_state
                break

        return agent_state

    @property
    def objects_state(self):
        """
        [
            {
            "objectId": str,
            "objectType": str,
            "name": str,
            "position": dict[str, float],
            "rotation": dict[str, float],
            "axisAlignedBoundingBox": dict[str, union[str, any]],
            "objectOrientedBoundingBox": dict[str, union[str, any]],
            }
        ]
        """
        return self.controller.last_event.metadata["objects"]

    @property
    def rgb_frame(self) -> np.ndarray:
        return self.controller.last_event.frame

    @property
    def depth_frame(self) -> np.ndarray:
        return self.controller.last_event.depth_frame

    def get_objectsByType(self, objectType):
        objects = []
        for object in self.objects_state:
            if object["objectType"].lower() == objectType.lower():
                objects.append(object)
        return objects

    def get_objectById(self, objectId):
        for object in self.objects_state:
            if object["objectId"] == objectId:
                return object
        else:
            return None

    def get_objectByName(self, objectName):
        for object in self.objects_state:
            if object["name"] == objectName:
                return object
        else:
            return None
        
    def get_closestObject(self, objects: list[object]):
        agent_pos = self.agent_state['position']
        
        def euclidean_distance(obj_pos):
            return (
                (obj_pos['x'] - agent_pos['x']) ** 2 +
                (obj_pos['y'] - agent_pos['y']) ** 2 +
                (obj_pos['z'] - agent_pos['z']) ** 2
            ) ** 0.5

        if not objects:
            return None

        closest_object = min(objects, key=lambda obj: euclidean_distance(obj['position']))
        return closest_object

    def log(self, success, message):
        if not message:
            return

        if success:
            log_msg = f"Frame {self.counter:03d} | [INFO] {message}"
        else:
            log_msg = f"Frame {self.counter:03d} | [ERROR] {message}"
        print(log_msg)
        self.log_archive[self.counter] = message


    def save_data(self, log_flag=True):
        """
        Save the event and rgb_frame of the current scene, and increment frame counter by 1
        """
        if log_flag:
            os.makedirs(f"{self.records_dir}/events", exist_ok=True)

            with open(
                f"{self.records_dir}/events/step_" + str(self.counter) + ".pickle", "wb"
            ) as handle:
                pickle.dump(
                    self.controller.last_event, handle, protocol=pickle.HIGHEST_PROTOCOL
                )
        os.makedirs(f"{self.records_dir}/ego_img", exist_ok=True)
        plt.imsave(
            f"{self.records_dir}/ego_img/step_" + str(self.counter) + ".png",
            np.asarray(self.rgb_frame, order="C"),
        )
        self.counter += 1

    def parse_word(self, line):
        line = line.strip().strip('()')
        parts = line.split()
        if parts[0] == 'pick-up':
            return f"pick up {parts[1]}"
        elif parts[0] == 'place-in':
            return f"place {parts[1]} in {parts[2]}"
        elif parts[0] == 'place-on':
            return f"place {parts[1]} on {parts[2]}"
        elif parts[0] == 'open':
            return f"open {parts[1]}"
        elif parts[0] == 'close':
            return f"close {parts[1]}"
        elif parts[0] == 'turn-on':
            return f"turn on {parts[1]}"
        elif parts[0] == 'turn-off':
            return f"turn off {parts[1]}"
        return None

    def load_plan_from_soln(self, soln_path: str):
        """problem.pddl.soln 파일을 읽어 자연어 명령 리스트로 반환"""
        commands = []
        with open(soln_path, 'r') as f:
            for line in f:
                nl = self.parse_word(line)
                if nl:
                    commands.append(nl)
        return commands


# Main execution
if __name__ == "__main__":
    # 1) task_context JSON 로드 (scene, init 상태 등)
    with open("environments/serveCoffee.json") as f:
        task_context = json.load(f)

    # 2) Thor 환경 초기화
    thor = Thor(task_context, scenario_idx=-1, records_dir="test/")
    time.sleep(1)

    # 3) PDDL 솔루션 불러와 자연어로 변환
    soln_path = "pddl_files/serveCoffee_problem.pddl.soln"
    commands = thor.load_plan_from_soln(soln_path)

    # 4) 자연어 명령을 action 클래스로 파싱
    actions = []
    for cmd in commands:
        for action_class in thor.action_space:
            args = action_class.parse(cmd)
            if args is not None:
                actions.append(action_class(thor, args))
                break

    # 5) 액션 순차 실행
    for idx, action in enumerate(actions, start=1):
        print(f"{idx}. Executing: {action}")
        action.execute()
        thor.log(success=True, message=f"after {action}")
        thor.save_data(log_flag=False)


    # 6) 마무리
    thor.controller.step(action="Done")
    thor.log(success=True, message="Plan Finished")
    thor.save_data()

    # 7) 이미지 → 비디오
    make_video_from_frames(
        records_dir=thor.records_dir,
        output_fname="plan_execution.mp4",
        fps=4
    )

    plan_success = check_task_success(thor) 
    if plan_success:
        thor.log(success=True, message="Task: succeeded")
        print("Task succeeded")
    else:
        thor.log(success=False, message="Task: failed")
        print("Task failed")
    thor.controller.stop()