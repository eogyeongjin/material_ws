import time
from .base_action import BaseAction

class PlaceOn(BaseAction):
    schema = '"place" <object> "on" <object>'

    def ground_objects(self) -> tuple[object, object]:
        target_object_type, destination_object_type = self.action_args

        # Check held object
        held = self.thor.agent_state.get("isHolding")

        # Special prioritization for StoveBurner
        candidates = self.thor.get_objectsByType(destination_object_type)
        if not candidates:
            return ()

        if destination_object_type.lower() == "StoveBurner".lower():
            empty_burners = [b for b in candidates if not b.get("receptacleObjectIds")]
            target_surface = self.thor.get_closestObject(empty_burners)
        else:
            target_surface = self.thor.get_closestObject(candidates)

        return (held, target_surface)

    def check_precondition(self, **kwargs) -> tuple[bool, str]:
        target_object = self.thor.agent_state.get("isHolding")
        destination_object = self.thor.get_objectById(kwargs['destination_object_id'])

        if not target_object:
            return False, f"{self.command} failed: Robot is not holding any object"

        if self.action_args[0].lower() not in target_object["objectType"].lower():
            return False, f"{self.command} failed: Robot is holding {target_object['objectType'].lower()}, not {self.action_args[0].lower()}"

        if not destination_object.get("receptacle", False):
            return False, f"{self.command} failed: {destination_object['objectType']} is not a receptacle"

        if destination_object['objectType'] == ["StoveBurner"] and destination_object.get("receptacleObjectIds"):
            return False, f"{self.command} failed: {destination_object['objectType']} already contains an object"

        elif destination_object['objectType'] in ['Toaster', 'CoffeeMachine']:
            if destination_object['isToggled']:
                return False, f"{destination_object['objectType']} is turned on"
            if destination_object.get('receptacleObjectIds'):
                return False, f"{destination_object['objectType']} is already occupied"

        return True, f"{self.command} can be executed"

    def execute(self) -> tuple[bool, str]:
        self.thor.log(success=True, message=self.command)
        self.thor.save_data()

        # Argument grounding
        grounded = self.ground_objects()
        if not grounded:
            return self.finish_action(False, f"Object Grounding Error for {self.command}: {self.action_args}")
        target_object, destination_object = grounded

        # Execution
        # self.move_to(destination_object["objectId"])

        success, message = self.check_precondition(destination_object_id=destination_object['objectId'])
        if not success:
            return self.finish_action(False, f"{self.command} failed: Precondition Violation for {self.command}: {message}")


        if destination_object["objectType"].lower() == "StoveBurner".lower():
            result = self.controller.step(
                action="PutObject",
                objectId=destination_object["objectId"],
                forceAction=True,
                placeStationary=True
            )

            stoveburners = self.thor.get_objectsByType(destination_object["objectType"])
            if not result.metadata['lastActionSuccess']:
                stoveburners = [s for s in stoveburners if s["objectId"] != destination_object["objectId"]]

                while stoveburners:
                    next_candidate = self.thor.get_closestObject(stoveburners)
                    result = self.controller.step(
                        action="PutObject",
                        objectId=next_candidate["objectId"],
                        forceAction=True,
                        placeStationary=True
                    )
                    if result.metadata['lastActionSuccess']:
                        destination_object = next_candidate
                        break
                    else:
                        stoveburners = [s for s in stoveburners if s["objectId"] != next_candidate["objectId"]]

        # elif destination_object["objectType"].lower() in ["CounterTop".lower(), "DiningTable".lower()]:
        #     for obj in self.thor.task_context["objects_init_state"]:
        #         if obj["objectType"] == target_object["objectType"]:
                    
        #             spawn_points = self.controller.step(
        #                 action="GetSpawnCoordinatesAboveReceptacle",
        #                 objectId=destination_object["objectId"],
        #                 anywhere=False
        #             ).metadata.get("actionReturn", [])
                                    
        #             self.controller.step(
        #                 action="PlaceObjectAtPoint",
        #                 objectId=target_object["objectId"],
        #                 position=obj["position"]
        #             )
        #             break
            # else:
            #     self.controller.step(
            #         action="PutObject",
            #         objectId=destination_object["objectId"],
            #         forceAction=True,
            #         placeStationary=True
            #     )
        else:
            self.controller.step(
                action="PutObject",
                objectId=destination_object["objectId"],
                forceAction=True,
                placeStationary=True
            )

            # # Get potential placement points
            # e = self.controller.step(
            #     action="GetSpawnCoordinatesAboveReceptacle",
            #     objectId=destination_object["objectId"],
            #     anywhere=False
            # )
            # place_locations = e.metadata.get("actionReturn", [])
            # if not place_locations:
            #     return self.finish_action(False, f"{self.command} failed: No valid place locations on {destination_object['objectType']}")
                        
            # agent_pos = self.thor.agent_state['position']
            # dest_pos = destination_object["position"]
            # place_locations.sort(
            #     key=lambda p: (p["x"] - dest_pos["x"])**2 + (p["z"] - dest_pos["z"])**2 +
            #                    0.5 * ((p["x"] - agent_pos["x"])**2 + (p["z"] - agent_pos["z"])**2)
            # )

            # counter = -1
            # while True:
            #     counter += 1
            #     # if too many trials, just drop the object
            #     if counter > 200:
            #         self.thor.log(success=False, message="PlaceObjectAt Point Failed. Putting Object...")
            #         self.controller.step(
            #             action="PutObject",
            #             objectId=destination_object["objectId"],
            #             forceAction=True,
            #             placeStationary=True
            #         )
            #         break
            #     result = self.controller.step(
            #         action="PlaceObjectAtPoint",
            #         objectId=target_object["objectId"],
            #         position=place_locations[counter]
            #     )
            #     if result.metadata['lastActionSuccess']:
            #         break

                
        success, message = self.check_success(target_object_id=target_object['objectId'], destination_object_id=destination_object['objectId'])
        if not success:
            return self.finish_action(success=False, message=f"{self.command} failed: Unachieved effect for {self.command}: {message}")
        
        # self.look_at(target_object['objectId'])
        
        return self.finish_action(success, message)

    def check_success(self, **kwargs) -> tuple[bool, str]:
        target_object = self.thor.get_objectById(kwargs['target_object_id'])
        destination_object = self.thor.get_objectById(kwargs['destination_object_id'])

        if not target_object or not destination_object:
            return False, f"{self.command} failed"

        if target_object['objectId'] not in destination_object.get('receptacleObjectIds', []):
            return False, f"{self.command} failed: {target_object['objectType']} was not placed on {destination_object['objectType']} ({self.controller.last_event.metadata['errorMessage']})"
        
        return True, f"{self.command} succeeded"
