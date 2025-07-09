import re
from abc import ABC, abstractmethod
import time
import math
import numpy as np
from typing import Dict, List
from collections import deque

class BaseAction(ABC):
    """
    Class variables and methods for initiating actions with natural-language commands
    """
    schema = ""
        
    @classmethod
    @property
    def template(cls):
        template = re.sub(r'"\s*([^"]+)\s*"', r'\1', cls.schema)
        template = re.sub(r'<([^>]+)>', r'(.*?)', template)
        return template
    
    @classmethod
    def parse(cls, action_string) -> tuple[str]:
        match = re.fullmatch(cls.template, action_string)
        if match:
            return match.groups()
        else:
            return None
   
    """
    Instance variables and methods for executing actions
    """
    def __init__(self, thor, action_args):
        self.thor = thor
        self.controller = thor.controller
        self.action_args = action_args
   
    @property
    def signature(self) -> str:
        action_name = self.__class__.__name__[0].lower() + self.__class__.__name__[1:]
        return f"{action_name}({', '.join(self.action_args)})"

    @property
    def command(self) -> str:
        schema_text = re.sub(r'<[^>]+>', '{}', self.schema).replace('"', '')
        return schema_text.format(*self.action_args).strip()

    @abstractmethod
    def ground_objects(self) -> tuple[object]:
        pass
   
    @abstractmethod
    def check_precondition(self, **kwargs) -> tuple[bool, str]:
        pass
   
    @abstractmethod
    def execute(self) -> tuple[bool, str]:
        pass       
    
    @abstractmethod
    def check_success(self, **kwargs) -> tuple[bool, str]:
        pass       

    def apply_conditional_effect(self, **kwargs) -> None:
        pass

    def finish_action(self, success, message, log_flag=True, sleep=0) -> tuple[bool, str]:
        # if self.thor.change_injector.tick():
        #     message = message + f" | Change Injected: {self.thor.change_injector.scenario}"
                
        self.thor.log(success=success, message=message)
        self.thor.save_data(log_flag)
        self.controller.step(action="Done")        
        time.sleep(sleep)
        return success, message    
    
    """
    Common helper functions for every primitive action
    """    
    def look_at(self, obj_id, center_to_camera_disp=0.675) -> tuple[bool, str]:
        target_obj = self.thor.get_objectById(obj_id)
        target_pos = target_obj['position']
        
        # Rotate Robot
        robot_pos = self.controller.last_event.metadata['agent']['position']
        robot_y = robot_pos['y'] + center_to_camera_disp
        yaw = math.degrees(math.atan2(
            target_pos['x'] - robot_pos['x'],
            target_pos['z'] - robot_pos['z']
        ))
        self.controller.step(
            action="Teleport",
            position=robot_pos,
            rotation=dict(x=0, y=yaw, z=0),
            forceAction=True
        )
        self.controller.step(action="Done")

        # Tilt Camera
        tilt = -math.degrees(math.atan2(
            target_pos['y'] - robot_y,
            math.sqrt(
                (target_pos['z'] - robot_pos['z'])**2 +
                (target_pos['x'] - robot_pos['x'])**2
            )
        ))
        tilt = round(tilt, 1)

        org_tilt = self.controller.last_event.metadata['agent']['cameraHorizon']
        final_tilt = tilt - org_tilt
        final_tilt = max(-30, min(60, final_tilt)) 

        if final_tilt > 0:
            self.controller.step(action="LookDown", degrees=abs(final_tilt))
        elif final_tilt < 0:
            self.controller.step(action="LookUp", degrees=abs(final_tilt))
        self.controller.step(action="Done")

        return self.finish_action(success=True, message="", log_flag=False, sleep=0)
  
    def move_to(self, obj_id) -> tuple[bool, str]:        
        target_obj = self.thor.get_objectById(obj_id)
                    
        reachable_positions = self.controller.step(action="GetReachablePositions").metadata["actionReturn"]
        reachable_points = self.get_2d_reachable_points(reachable_positions)
        closest_pos = self.closest_position(target_obj["position"], reachable_positions)
        robot_pos = self.controller.last_event.metadata['agent']['position']
        target_pos_val = [closest_pos['x'], closest_pos['z']]

        # def rounded(literal):
        #     return round(literal, 2)

        # grid = self.create_graph()
        # robot_x = robot_y = 0
        # target_x = target_y = 0
        # for row in range(grid.shape[0]):
        #     for col in range(grid.shape[1]):
        #         if [rounded(robot_pos['x']), rounded(robot_pos['z'])] == [rounded(grid[row, col, 0]), rounded(grid[row, col, 1])]:
        #             robot_x, robot_y = row, col
        #         if [rounded(target_pos_val[0]), rounded(target_pos_val[1])] == [rounded(grid[row, col, 0]), rounded(grid[row, col, 1])]:
        #             target_x, target_y = row, col

        # path = self.find_path(
        #     grid, start=(robot_x, robot_y), goal=(target_x, target_y),
        #     reachable_points=reachable_points
        # )
        # if path is None:
        #     return self.finish_action(success=False, message=f"No valid path is found from robot to {target_obj['objectType']}", log_flag=False)

        # for p in path:
        #     x = grid[p.x, p.y, 0]
        #     z = grid[p.x, p.y, 1]
        #     y = 0.9
        #     self.look_at(obj_id)
        #     self.controller.step(
        #         action="Teleport",
        #         position=dict(x=x, y=y, z=z),
        #         forceAction=True,
        #         standing=True
        #     )

        self.controller.step(
            action="Teleport",
            position=closest_pos,
            forceAction=True,
            standing=True
        )


        return self.look_at(obj_id) 

    def create_graph(self, gridSize=0.25, min=-5, max=5.1):
        grid = np.mgrid[min:max:gridSize, min:max:gridSize].transpose(1,2,0)
        return grid

    def find_path(self, grid, start, goal, reachable_points):
        """
        BFS-based start -> goal path
        start: (x, y) grid index
        goal: (x, y) grid index
        """
        class Node:
            def __init__(self, x, y, parent=None):
                self.x = x
                self.y = y
                self.parent = parent

        def get_path(node):
            path_ = []
            while node:
                path_.append(node)
                node = node.parent
            return path_[::-1]

        def is_valid(nx, ny, N):
            if nx < 0 or ny < 0 or nx >= N or ny >= N:
                return False
            val = grid[nx, ny]
            if [val[0], val[1]] not in reachable_points.tolist():
                return False
            return True

        N = grid.shape[0]
        visited = set()
        q = deque()
        src_node = Node(start[0], start[1], None)
        q.append(src_node)
        visited.add((src_node.x, src_node.y))

        ROW = [-1, 0, 0, 1]
        COL = [0, -1, 1, 0]

        while q:
            cur = q.popleft()
            if (cur.x, cur.y) == (goal[0], goal[1]):
                return get_path(cur)

            for i in range(4):
                nx = cur.x + ROW[i]
                ny = cur.y + COL[i]
                if is_valid(nx, ny, N) and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    q.append(Node(nx, ny, cur))
        return None
    
    def closest_position(
        self,
        object_position: Dict[str, float],
        reachable_positions: List[Dict[str, float]]
    ) -> Dict[str, float]:
        out = reachable_positions[0]
        min_distance = float('inf')
        for pos in reachable_positions:
            # NOTE: y is the vertical direction, so only care about the x/z ground positions
            dist = sum([(pos[key] - object_position[key]) ** 2 for key in ["x", "z"]])
            if dist < min_distance:
                min_distance = dist
                out = pos
        return out
    
    def get_2d_reachable_points(self, reachable_positions):
        reachable_points = []
        for p in reachable_positions:
            reachable_points.append([p['x'], p['z']])
        reachable_points = np.array(reachable_points)
        return reachable_points