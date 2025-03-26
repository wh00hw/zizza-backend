import uuid
import threading
from fastapi import FastAPI
from typing import List, Dict, Any
from zizza.api import API

app = FastAPI()
tasks = {}
api = API()

def execute_operations(task_id: str, operations: List[Dict[str, Any]]):
    operations_count = len(operations)
    for index, operation in enumerate(operations):
        command = operation.get("command")
        params = operation.get("params", {})
        tasks[task_id]['status'] = f"Processing {index + 1}/{operations_count}"

        try:
            if not command or not isinstance(params, dict):
                raise ValueError("Invalid command format")
            
            method = getattr(api, command, None)
            if not callable(method):
                raise ValueError(f"Unknown command: {command}")
            
            tasks[task_id]['results'].append({"command": command, "params": params, "result": method(**params)})
        except Exception as e:
            tasks[task_id]['status'] = f"Failed at {index + 1}/{operations_count}"
            tasks[task_id]['results'].append({"command": command, "params": params, "error": str(e)})
            return
            
    tasks[task_id]['status'] = "Completed"

@app.post("/execute")
def execute(operations: List[Dict[str, Any]]):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "Pending", "results": []}
    
    thread = threading.Thread(target=execute_operations, args=(task_id, operations))
    thread.start()
    
    return {"task_id": task_id}

@app.get("/status/{task_id}")
def get_status(task_id: str):
    return tasks.get(task_id, {"error": "Task not found"})