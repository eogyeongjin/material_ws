from .base_action import BaseAction

class Wait(BaseAction):
    schema = '"wait until" <object> "is" <attribute>'
    
    def ground_objects(self) -> tuple[object]:
        target_object_type = self.action_args[0]
        
        target_object_candidates = self.thor.get_objectsByType(target_object_type)
        if len(target_object_candidates) == 0:
            return ()
        else:
            target_object = self.thor.get_closestObject(target_object_candidates)            
            return (target_object,)
    
    def check_precondition(self, **kwargs) -> tuple[bool, str]:
        return True, f"{self.command} can be executed"
    
    def execute(self) -> tuple[bool, str]:
        self.thor.log(success=True, message=self.command)
        self.thor.save_data()
        return self.finish_action(success=True, message=f"{self.command} succeeded")
    
    def check_success(self, **kwargs) -> tuple[bool, str]:
        return True, f"{self.command} succeeded"
