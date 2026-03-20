import cv2
import numpy as np
import base64
import logging
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from ..services.face_service import FaceService
from ..utils.logger import DetectionLogger
from ..services.storage_service import StorageService
from ..services.progress_store import progress_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
storage = StorageService()
face_service = FaceService(storage)
det_logger = DetectionLogger(storage)


# ------------------------------------------------------------------ #
# Webcam streaming                                                     #
# ------------------------------------------------------------------ #

def gen_frames():
    """Video streaming generator — processes every 3rd frame for speed."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return

    frame_count = 0
    last_frame = None

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame_count += 1
        if frame_count % 3 == 0 or last_frame is None:
            try:
                last_frame, _ = face_service.process_frame(frame)
            except Exception as exc:
                logger.error(f"process_frame error: {exc}")
                last_frame = frame

        ret, buffer = cv2.imencode(
            ".jpg", last_frame, [cv2.IMWRITE_JPEG_QUALITY, 75]
        )
        if not ret:
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )

    cap.release()


@router.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ------------------------------------------------------------------ #
# Image upload detection (async with progress)                         #
# ------------------------------------------------------------------ #

def run_async_detection(task_id: str, img: np.ndarray):
    """Synchronous background task for upload-based detection."""
    try:
        processed_img, detections = face_service.process_frame(img, task_id=task_id)

        if detections:
            best = max(detections, key=lambda d: d["confidence"])
            det_logger.log_detection(best["name"], best["confidence"], source="upload")

        _, buffer = cv2.imencode(".jpg", processed_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        img_b64 = base64.b64encode(buffer).decode("utf-8")

        progress_store.set_result(task_id, {
            "detections": detections,
            "image": f"data:image/jpeg;base64,{img_b64}",
        })
    except Exception as exc:
        logger.error(f"Detection task error: {exc}")
        progress_store.update_progress(task_id, 100, f"Error: {exc}")
        progress_store.set_result(task_id, {"error": str(exc)})


@router.post("/upload")
async def upload_image(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    task_id = progress_store.create_task()
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Invalid image — could not decode file"}

        background_tasks.add_task(run_async_detection, task_id, img)
        return {"task_id": str(task_id)}
    except Exception as exc:
        logger.error(f"Upload error: {exc}")
        return {"error": str(exc)}


# ------------------------------------------------------------------ #
# Progress & result polling                                            #
# ------------------------------------------------------------------ #

@router.get("/progress/{task_id}")
async def get_progress(task_id: str):
    task = progress_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "progress": task["progress"],
        "status": task["status"],
        "complete": task["progress"] == 100,
    }


@router.get("/result/{task_id}")
async def get_result(task_id: str):
    task = progress_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task["result"]:
        return {"error": "Result not ready yet"}
    return task["result"]


# ------------------------------------------------------------------ #
# Target face matching (1 vs Many)                                     #
# ------------------------------------------------------------------ #

def run_match_task(task_id: str, target_img: np.ndarray, group_img: np.ndarray):
    """Synchronous background task for face matching."""
    try:
        processed_img, result = face_service.match_faces(target_img, group_img, task_id)

        _, buffer = cv2.imencode(".jpg", processed_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        img_b64 = base64.b64encode(buffer).decode("utf-8")

        progress_store.set_result(task_id, {
            "match_data": result,
            "image": f"data:image/jpeg;base64,{img_b64}",
        })
    except Exception as exc:
        logger.error(f"Match task error: {exc}")
        progress_store.update_progress(task_id, 100, f"Error: {exc}")
        progress_store.set_result(task_id, {"error": str(exc)})


@router.post("/match")
async def match_images(
    background_tasks: BackgroundTasks,
    target: UploadFile = File(...),
    group: UploadFile = File(...),
):
    task_id = progress_store.create_task()
    try:
        t_bytes = await target.read()
        g_bytes = await group.read()

        target_img = cv2.imdecode(np.frombuffer(t_bytes, np.uint8), cv2.IMREAD_COLOR)
        group_img = cv2.imdecode(np.frombuffer(g_bytes, np.uint8), cv2.IMREAD_COLOR)

        if target_img is None or group_img is None:
            return {"error": "Invalid image(s) provided"}

        background_tasks.add_task(run_match_task, task_id, target_img, group_img)
        return {"task_id": str(task_id)}
    except Exception as exc:
        logger.error(f"Match upload error: {exc}")
        return {"error": str(exc)}
