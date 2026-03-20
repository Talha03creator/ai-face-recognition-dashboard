from fastapi import APIRouter, UploadFile, File, Form
from ..services.face_service import FaceService
from ..services.storage_service import StorageService
import cv2
import numpy as np

router = APIRouter()
storage = StorageService()
face_service = FaceService(storage)

@router.post("/register")
async def register_user(name: str = Form(...), file: UploadFile = File(...)):
    """Register a new user with an uploaded image or camera capture."""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    success = face_service.register_user(name, img)
    if success:
        return {"status": "success", "message": f"User {name} registered."}
    else:
        return {"status": "error", "message": "Could not detect face in image."}

@router.get("/")
async def list_users():
    """List all registered users."""
    return {"users": storage.get_all_users()}

@router.delete("/{name}")
async def delete_user(name: str):
    """Delete a user and their encodings."""
    storage.delete_user(name)
    # Re-generate and reload encodings
    # (Simplified: wipe encodings in the dict and save)
    history = storage.load_encodings()
    if name in history:
        del history[name]
    storage.save_encodings(history)
    face_service.load_known_faces()
    return {"status": "success", "message": f"User {name} deleted."}
