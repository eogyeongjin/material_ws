import time
from .base_action import BaseAction

class Open(BaseAction):
    schema = '"open" <object>'
    
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
    
        if not target_object['openable']:
            return False, f"{self.command} failed: {target_object['objectType']} is not an openable object"

        if target_object['isOpen']:
            return False, f"{self.command} failed: {target_object['objectType']} is already open"            
                    
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
            action="OpenObject",
            objectId=target_object["objectId"],
            openness=1,
            forceAction=True
        )
                
        success, message = self.check_success(target_object_id=target_object["objectId"])    
        if not success:
            return self.finish_action(success=False, message=f"{self.command} failed: Unachieved effect for {self.command}: {message}")
        
        # self.look_at(target_object["objectId"])
        
        return self.finish_action(success=success, message=message)

    def check_success(self, **kwargs) -> tuple[bool, str]:
        target_object = self.thor.get_objectById(kwargs['target_object_id'])

        if not target_object['isOpen']:
            return False, f"{self.command} failed: {target_object['objectType']} was not openned ({self.controller.last_event.metadata['errorMessage']})"
        
        return True, f"{self.command} succeeded"