# actions/__init__.py
import os
import importlib
import inspect
from pathlib import Path
from .base_action import BaseAction
from .wait_action import Wait

package_dir = Path(__file__).parent

__all_classes__ = []

for file in package_dir.glob("*.py"):
    if file.name in ["__init__.py", "base_action.py"]:
        continue

    module_name = f"{__name__}.{file.stem}"
    module = importlib.import_module(module_name)

    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseAction) and obj is not BaseAction and obj is not Wait:
            __all_classes__.append(obj)

__all__ = ["get_action_classes"]

def get_action_classes():
    return __all_classes__