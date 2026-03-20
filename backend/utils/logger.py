from datetime import datetime
from typing import Optional
from ..services.storage_service import StorageService

class DetectionLogger:
    def __init__(self, storage_service: StorageService):
        self.storage = storage_service

    def log_detection(self, name: str, confidence: float, source: str = "webcam"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "name": name,
            "confidence": f"{confidence:.2f}",
            "source": source
        }
        self.storage.add_log(entry)
