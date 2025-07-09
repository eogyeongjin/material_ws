from .base_action import BaseAction

class TurnOn(BaseAction):
    schema = '"turn on" <object>'
    
    def ground_objects(self) -> tuple[object]:
        target_object_type = self.action_args[0]
        
        target_object_candidates = self.thor.get_objectsByType(target_object_type)
        if len(target_object_candidates) == 0:
            return ()
        else:
            # StoveBurner -> StoveKnob
            if target_object_type.lower() == "StoveBurner".lower():
                target_object = self.thor.get_closestObject(target_object_candidates)
                for stoveknob in self.thor.get_objectsByType("StoveKnob"):
                    if stoveknob['controlledObjects'][0] == target_object['objectId']:
                        target_object = stoveknob
            else:
                target_object = self.thor.get_closestObject(target_object_candidates)
                
            return (target_object,)
    
    def check_precondition(self, **kwargs) -> tuple[bool, str]:
        target_object = self.thor.get_objectById(kwargs['target_object_id'])
    
        if not target_object['toggleable']:
            return False, f"{self.command} failed: {target_object['objectType']} is not a toggleable object"
        
        if target_object['isToggled']:
            return False, f"{self.command} failed: {target_object['objectType']} is already turned on"
        
        if target_object['objectType'] == 'Microwave' and target_object['isOpen']:
            return False, f"{self.command} failed: {target_object['objectType']} cannot be turned on if it is open"
                    
        return True, f"{self.command} can be executed"
    
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
            action="ToggleObjectOn",
            objectId=target_object["objectId"],
            forceAction=True
        )
        
        success, message = self.check_success(target_object_id=target_object["objectId"])    
        if not success:
            return self.finish_action(success=False, message=f"{self.command} failed: Unachieved effect for {self.command}: {message}")
        
        # self.look_at(target_object["objectId"])
        
        self.apply_conditional_effect(target_object_id=target_object["objectId"])
                
        return self.finish_action(success=success, message=message)

    def check_success(self, **kwargs) -> tuple[bool, str]:
        target_object = self.thor.get_objectById(kwargs['target_object_id'])

        if not target_object['isToggled']:
            return False, f"{self.command} failed: {target_object['objectType']} is still off ({self.controller.last_event.metadata['errorMessage']})"
        
        return True, f"{self.command} succeeded"

    def apply_conditional_effect(self, **kwargs) -> None:
        target_object = self.thor.get_objectById(kwargs['target_object_id'])
        if target_object["objectType"].lower() == "Faucet".lower():
            # If faucet is turned on, clean dirty objects and fill fillable objects with water in sinkbasin 
            # Required as not every object in the sink is assumed to be under the faucet
            sinkbasin = self.thor.get_objectsByType("SinkBasin")[0] # Assume only a single sink within the environment
            for obj_id in sinkbasin['receptacleObjectIds']:
                obj = self.thor.get_objectById(obj_id)
                self.controller.step(
                    action="CleanObject",
                    objectId=obj["objectId"],
                    forceAction=True
                )
                if obj["canFillWithLiquid"] and not obj["isFilledWithLiquid"]:
                    self.controller.step(
                        action="FillObjectWithLiquid",
                        objectId=obj["objectId"],
                        fillLiquid="water",
                        forceAction=True
                    )
        else:
            return
