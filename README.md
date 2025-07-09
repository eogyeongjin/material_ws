# Task Planning - PDDL

## Environment Setup
```
# Optional
python3.10 -m venv venv
source venv/bin/activate

# Setup
pip install -r requirements.txt
```

## PDDL Planning
```bash
# pyperplan -l warning -s astar -H hff ./pddl_files/domain.pddl ./pddl_files/problem.pddl

```
You have to define domain.pddl and problem.pddl in `task_planning/pddl_files` 


## Action Execution
```bash
python3 execute_thor.py
```


