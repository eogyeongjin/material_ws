import time
from .base_action import BaseAction

class PickUp(BaseAction):
    schema = '"pick up" <object>'

    def ground_objects(self) -> tuple[object]:
        target_object_type = self.action_args[0]  # 예: 'apple' or 'Apple'
        target_type_lower = target_object_type.lower()

        # 기준 타입 매핑 (lowercase → PascalCase)
        sliced_set = {"apple", "bread", "lettuce", "potato", "tomato"}
        cracked_set = {"egg"}

        def to_pascal_case(word: str) -> str:
            return word[0].upper() + word[1:].lower()

        canonical_type = to_pascal_case(target_object_type)

        if target_type_lower in sliced_set:
            candidates = self.thor.get_objectsByType(canonical_type + "Sliced")[2:]
            if not candidates:
                candidates = self.thor.get_objectsByType(canonical_type)
        elif target_type_lower in cracked_set:
            candidates = self.thor.get_objectsByType(canonical_type + "Cracked")
            if not candidates:
                candidates = self.thor.get_objectsByType(canonical_type)
        else:
            candidates = self.thor.get_objectsByType(canonical_type)

        if not candidates:
            return ()

        target_object = candidates[0]
        return (target_object,)

    def check_precondition(self, **kwargs) -> tuple[bool, str]:
        target_object = self.thor.get_objectById(kwargs['target_object_id'])

        if not self.thor.is_hand_empty:
            return False, f"{self.command} failed: Robot is already holding an object, cannot pick up {target_object['objectType']}"
        
        if not target_object.get('pickupable', False):
            return False, f"{self.command} failed: {target_object['objectType']} is not a pickupable object"
        
        return True, f"{self.command} failed: {self.command} can be executed"

    def execute(self) -> tuple[bool, str]:
        self.thor.log(success=True, message=self.command)
        self.thor.save_data()

        # Argument grounding
        grounded_objects = self.ground_objects()
        if not grounded_objects:
            return self.finish_action(success=False, message=f"{self.command} failed: Object Grounding Error for {self.command}: {self.action_args}")
        target_object = grounded_objects[0]

        # Execution
        # self.move_to(target_object["objectId"])

        success, message = self.check_precondition(target_object_id=target_object["objectId"])
        if not success:
            return self.finish_action(success=False, message=f"{self.command} failed: Precondition Violation for {self.command}: {message}")

        self.controller.step(
            action="PickupObject",
            objectId=target_object["objectId"],
            forceAction=True,
            manualInteract=False
        )

        # self.look_at(target_object["objectId"])

        success, message = self.check_success(target_object_id=target_object["objectId"])    
        if not success:
            return self.finish_action(success=False, message=f"{self.command} failed: Unachieved effect for {self.command}: {message}")

        # self.look_at(target_object['objectId'])

        return self.finish_action(success=success, message=message)

    def check_success(self, **kwargs) -> tuple[bool, str]:
        target_object = self.thor.get_objectById(kwargs['target_object_id'])

        held_obj = self.thor.agent_state.get("isHolding")
        if not held_obj or held_obj.get("objectId") != target_object["objectId"]:
            return False, f"{self.command} failed: {target_object['objectType']} was not picked up ({self.controller.last_event.metadata['errorMessage']})"

        return True, f"{self.command} succeeded"
