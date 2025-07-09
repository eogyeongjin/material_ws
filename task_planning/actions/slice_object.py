from .base_action import BaseAction

class Slice(BaseAction):
    schema = '"slice" <object>'

    def ground_objects(self) -> tuple[object]:
        target_object_type = self.action_args[0]
        target_object_candidates = self.thor.get_objectsByType(target_object_type)
        if len(target_object_candidates) == 0:
            return ()
        else:
            target_object = self.thor.get_closestObject(target_object_candidates)
            return (target_object,)

    def check_precondition(self, **kwargs) -> tuple[bool, str]:
        target_object = self.thor.get_objectById(kwargs['target_object_id'])

        # Check if the robot is holding a Knife
        holding = self.thor.agent_state.get('isHolding')
        if not holding or holding["objectType"] != "Knife":
            return False, f"{self.command} failed: Robot must be holding a Knife to slice an object"

        # Check if the target object is sliceable
        if not target_object.get("sliceable", False):
            return False, f"{self.command} failed: {target_object['objectType']} is not sliceable"

        return True, f"{self.command} can be executed"

    def execute(self) -> tuple[bool, str]:
        self.thor.log(success=True, message=self.command)
        self.thor.save_data()

        # Argument grounding
        grounded_objects = self.ground_objects()
        if not grounded_objects:
            return self.finish_action(success=False, message=f"{self.command} failed: Object Grounding Error for {self.command}: {self.action_args}")        
        target_object = grounded_objects[0]

        # Execute
        # self.move_to(target_object["objectId"])

        success, message = self.check_precondition(target_object_id=target_object["objectId"])
        if not success:
            return self.finish_action(success=False, message=f"{self.command} failed: Precondition Violation for {self.command}: {message}")

        self.controller.step(
            action="SliceObject",
            objectId=target_object["objectId"],
            forceAction=True
        )
        
        # self.look_at(target_object["objectId"])

        success, message = self.check_success(target_object_id=target_object["objectId"])
        if not success:
            return self.finish_action(success=False, message=f"{self.command} failed: Unachieved effect for {self.command}: {message}")

        return self.finish_action(success=success, message=message)

    def check_success(self, **kwargs) -> tuple[bool, str]:
        target_object = self.thor.get_objectById(kwargs['target_object_id'])

        # After slicing, slicedObjectIds should not be empty
        if not target_object['isSliced']:
            return False, f"{self.command} failed: {target_object['objectType']} was not sliced ({self.controller.last_event.metadata['errorMessage']})"
        
        return True, f"{self.command} succeeded"
