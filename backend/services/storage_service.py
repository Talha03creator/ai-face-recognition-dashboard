import os
import json
import pickle
import shutil
from pathlib import Path
from typing import List, Dict, Any

class StorageService:
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.users_path = self.base_path / "users"
        self.encodings_file = self.base_path / "encodings.pkl"
        self.logs_file = self.base_path / "logs.json"
        
        self._ensure_dirs()

    def _ensure_dirs(self):
        self.users_path.mkdir(parents=True, exist_ok=True)
        if not self.logs_file.exists():
            with open(self.logs_file, "w") as f:
                json.dump([], f)

    def save_user_image(self, name: str, image_bytes: bytes) -> str:
        user_dir = self.users_path / name
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Simple incrementing filename
        count = len(list(user_dir.glob("*.jpg")))
        file_path = user_dir / f"face_{count + 1}.jpg"
        
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
        return str(file_path)

    def get_all_users(self) -> List[str]:
        return [d.name for d in self.users_path.iterdir() if d.is_dir()]

    def delete_user(self, name: str):
        user_dir = self.users_path / name
        if user_dir.exists():
            shutil.rmtree(user_dir)

    def save_encodings(self, encodings_dict: Dict[str, Any]):
        with open(self.encodings_file, "wb") as f:
            pickle.dump(encodings_dict, f)

    def load_encodings(self) -> Dict[str, Any]:
        if not self.encodings_file.exists():
            return {}
        with open(self.encodings_file, "rb") as f:
            return pickle.load(f)

    def add_log(self, log_entry: Dict[str, Any]):
        logs = self.get_logs()
        logs.append(log_entry)
        # Keep last 1000 logs
        logs = logs[-1000:]
        with open(self.logs_file, "w") as f:
            json.dump(logs, f, indent=2)

    def get_logs(self) -> List[Dict[str, Any]]:
        if not self.logs_file.exists():
            return []
        try:
            with open(self.logs_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
