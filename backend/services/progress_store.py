from typing import Dict, Any, Optional
import uuid

class ProgressStore:
    def __init__(self):
        # Format: { task_id: { "progress": int, "status": str, "result": any } }
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self) -> str:
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "progress": 0,
            "status": "Initializing",
            "result": None
        }
        return task_id

    def update_progress(self, task_id: str, progress: int, status: str):
        if task_id in self.tasks:
            self.tasks[task_id]["progress"] = progress
            self.tasks[task_id]["status"] = status

    def set_result(self, task_id: str, result: Any):
        if task_id in self.tasks:
            self.tasks[task_id]["progress"] = 100
            self.tasks[task_id]["status"] = "Complete"
            self.tasks[task_id]["result"] = result

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)

    def cleanup(self, task_id: str):
        if task_id in self.tasks:
            del self.tasks[task_id]

# Singleton instance
progress_store = ProgressStore()
