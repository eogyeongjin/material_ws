from .base_action import BaseAction
import numpy as np

class PlaceIn(BaseAction):
    schema = '"place" <object> "in" <object>'

    def ground_objects(self) -> tuple[object, object]:
        target_object_type, destination_object_type = self.action_args

        if destination_object_type.lower() == "Sink".lower():
            destination_object_type = "SinkBasin"

        destination_candidates = self.thor.get_objectsByType(destination_object_type)
        if not destination_candidates:
            return ()
    
        if destination_candidates[0]['openable']:
            destination_candidates = [obj for obj in destination_candidates if obj.get("isOpen", False)]
            if not destination_candidates:
                return ()
        
        destination_object = self.thor.get_closestObject(destination_candidates)
        
        held = self.thor.agent_state.get("isHolding")
        if not held:
            return ()

        return (held, destination_object)

    def check_precondition(self, **kwargs) -> tuple[bool, str]:
        target_object = self.thor.get_objectById(kwargs['target_object_id'])
        destination_object = self.thor.get_objectById(kwargs['destination_object_id'])

        if not target_object or self.action_args[0].lower() not in target_object["objectType"].lower():
            return False, f"{self.command} failed: Robot is not holding the correct object to place in"

        if destination_object['objectType'] == 'Microwave':
            if not destination_object['isOpen']:
                return False, f"{destination_object['objectType']} is not open"
            if destination_object.get('receptacleObjectIds'):
                return False, f"{destination_object['objectType']} is already occupied"
        elif destination_object['objectType'] == 'Fridge':
            if not destination_object['isOpen']:
                return False, f"{destination_object['objectType']} is not open"
        elif destination_object['objectType'] in ['Toaster', 'CoffeeMachine']:
            if destination_object['isToggled']:
                return False, f"{destination_object['objectType']} is turned on"
            if destination_object.get('receptacleObjectIds'):
                return False, f"{destination_object['objectType']} is already occupied"
        elif destination_object['objectType'] == 'StoveBurner':
            if destination_object.get('receptacleObjectIds'):
                return False, f"{destination_object['objectType']} is already occupied"

        return True, f"{self.command} can be executed"

    def execute(self) -> tuple[bool, str]:
        self.thor.log(success=True, message=self.command)
        self.thor.save_data()

        # Argument grounding
        grounded_objects = self.ground_objects()
        if not grounded_objects:
            return self.finish_action(False, f"{self.command} failed: Object Grounding Error for {self.command}: {self.action_args}")
        target_object, destination_object = grounded_objects

        # Execution
        # self.move_to(destination_object["objectId"])

        success, message = self.check_precondition(target_object_id=target_object['objectId'], destination_object_id=destination_object['objectId'])
        if not success:
            return self.finish_action(False, f"{self.command} failed: Precondition Violation for {self.command}: {message}")

        result = self.controller.step(
            action="PutObject",
            objectId=destination_object["objectId"],
            forceAction=True,
            placeStationary=True
        )
        if not result.metadata['lastActionSuccess']:
            e = self.controller.step(
                    action="GetSpawnCoordinatesAboveReceptacle",
                    objectId=destination_object["objectId"],
                    anywhere=True
                )
            place_locations = e.metadata.get("actionReturn", [])
            if not place_locations:
                return self.finish_action(False, f"{self.command} failed: No valid place locations on {destination_object['objectType']}")

            # Choose the closest location to the robot
            dest_pos = destination_object["position"]
            place_locations.sort(
                key=lambda p: (p["x"] - dest_pos["x"])**2 + (p["z"] - dest_pos["z"])**2
            )
            counter = -1
            while True:
                counter += 1
                if counter > 200:
                    self.execute_alternative(destination_object['objectId'])
                else:
                    result = self.controller.step(
                        action="PlaceObjectAtPoint",
                        objectId=target_object["objectId"],
                        position=place_locations[counter]
                    )
                
                    if result.metadata['lastActionSuccess']:
                        break

        success, message = self.check_success(target_object_id=target_object['objectId'], destination_object_id=destination_object['objectId'])
        
        # self.look_at(destination_object['objectId'])
        
        return self.finish_action(success, message)

    def check_success(self, **kwargs) -> tuple[bool, str]:
        target_object = self.thor.get_objectById(kwargs['target_object_id'])
        destination_object = self.thor.get_objectById(kwargs['destination_object_id'])
        
        if target_object['objectId'] not in destination_object.get('receptacleObjectIds', []):
            return False, f"{self.command} failed: {target_object['objectType']} was not placed in {destination_object['objectType']} ({self.controller.last_event.metadata['errorMessage']})"
        
        return True, f"{self.command} succeeded"
    
        
    def execute_alternative(self, destination_id: str) -> tuple[bool, str]:
        destination_object = self.thor.get_objectById(destination_id)
        place_location = destination_object['position']        
        robot_pos = self.thor.agent_state['position']
        
        # Look straight (tilt = 0)
        tilt = self.thor.agent_state['cameraHorizon']
        tilt = np.round(tilt, 1)
        if tilt > 0:
            e = self.controller.step(action="LookUp", degrees=tilt)
        else:
            e = self.controller.step(action="LookDown", degrees=tilt)
        self.controller.step(action="Done")

        # Move object over receptacle
        dist = np.sqrt((robot_pos['x'] - place_location['x'])**2 + (robot_pos['z'] - place_location['z'])**2)
        dist = np.round(dist, 1) - 0.4

        e = self.controller.step(
            action="MoveHeldObjectAhead",
            moveMagnitude=dist,
            forceVisible=False
        )
        self.controller.step(action='Done')
        
        # Drop object
        e = self.controller.step(
            action="DropHandObject",
            forceAction=False
        )
        self.controller.step(action='Done')

        # Look at the receptacle again
        if tilt > 0:
            e = self.controller.step(action="LookDown", degrees=tilt)
        else:
            e = self.controller.step(action="LookUp", degrees=tilt)
            
        self.controller.step(action="Done")