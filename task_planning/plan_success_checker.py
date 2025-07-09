def get_objectsByType(objects_state, objectType):
    objects = []
    for object_state in objects_state:
        if object_state["objectType"].lower() == objectType.lower():
            objects.append(object_state)
    return objects

def get_objectById(objects_state, objectId):
    for object in objects_state:
        if object["objectId"] == objectId:
            return object
    else:
        return None

def check_task_success(thor) -> bool:
    task_idx = thor.task_context["task_idx"]

    # ---------- 7. store utensils ----------
    if task_idx == 1:
        drawers = thor.get_objectsByType("Drawer")

        for drawer in drawers:
            receptacle_ids = drawer.get("receptacleObjectIds") or []

            has_spoon   = any("Spoon"   in obj_id for obj_id in receptacle_ids)
            has_fork    = any("Fork"    in obj_id for obj_id in receptacle_ids)
            drawer_closed = not drawer.get("isOpen", True)

            # print(f"Drawer {drawer['objectId']}: S={has_spatula} Sp={has_spoon} F={has_fork} K={has_knife} Closed={drawer_closed}")

            if has_spoon and has_fork and drawer_closed:
                return True

        return False

    # ---------- 5. serve coffee ----------
    elif task_idx == 5:
        mug = thor.get_objectsByType("Mug")[0]
        fridge = thor.get_objectsByType("Fridge")[0]

        # 1) Mug must be filled with coffee
        mug_filled_with_coffee = (
            mug.get("isFilledWithLiquid") and
            mug.get("fillLiquid") == "coffee"
        )

        # 2) Mug must be in fridge
        mug_in_fridge = fridge["objectId"] in (mug.get("parentReceptacles") or [])

        # print(mug_filled_with_coffee, mug_in_fridge)

        if mug_filled_with_coffee and mug_in_fridge:
            return True

        return False