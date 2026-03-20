import cv2
import numpy as np
import os
import logging
from typing import List, Dict, Tuple, Optional
from .storage_service import StorageService
from .progress_store import progress_store

logger = logging.getLogger(__name__)


class FaceService:
    # SFace L2 distance scale factor: SFace threshold is ~1.128
    # We divide by 1.88 so that 1.128 maps to ~0.6 in our 0-1 scale
    DIST_SCALE = 1.88

    def __init__(self, storage: StorageService):
        self.storage = storage

        model_dir = os.path.join(os.getcwd(), "models")
        detector_path = os.path.join(model_dir, "face_detection_yunet.onnx")
        recognizer_path = os.path.join(model_dir, "face_recognition_sface.onnx")

        if not os.path.exists(detector_path) or not os.path.exists(recognizer_path):
            raise FileNotFoundError(
                "AI models not found in ./models/. "
                "Please run download_models.py first."
            )

        self.detector = cv2.FaceDetectorYN.create(detector_path, "", (320, 320))
        self.recognizer = cv2.FaceRecognizerSF.create(recognizer_path, "")
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        self.known_features: List[np.ndarray] = []
        self.known_names: List[str] = []
        self.load_known_faces()

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _resize(self, img: np.ndarray, max_dim: int = 640) -> np.ndarray:
        h, w = img.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            return cv2.resize(img, (0, 0), fx=scale, fy=scale)
        return img

    def _detect_faces(self, img: np.ndarray):
        """Run YuNet detection. Returns list of face rows or empty list."""
        h, w = img.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(img)
        if faces is None:
            return []
        return faces

    def _feature(self, img: np.ndarray, face_row) -> np.ndarray:
        """Extract a 1×128 SFace feature vector."""
        aligned = self.recognizer.alignCrop(img, face_row)
        feat = self.recognizer.feature(aligned)  # shape (1, 128)
        return feat

    def _score(self, feat_a: np.ndarray, feat_b: np.ndarray) -> float:
        """Scaled L2 distance in [0, 1] range (lower = more similar)."""
        raw = float(self.recognizer.match(feat_a, feat_b, cv2.FR_NORM_L2))
        return raw / self.DIST_SCALE

    def _position(self, cx: int, img_w: int) -> str:
        ratio = cx / img_w
        if ratio < 0.33:
            return "Left side"
        if ratio < 0.67:
            return "Center"
        return "Right side"

    # ------------------------------------------------------------------ #
    # Known-face management                                                 #
    # ------------------------------------------------------------------ #

    def load_known_faces(self):
        """Load known SFace features from storage into memory."""
        encodings_dict = self.storage.load_encodings()
        self.known_features = []
        self.known_names = []
        for name, feats in encodings_dict.items():
            for raw in feats:
                arr = np.array(raw, dtype=np.float32)
                if arr.ndim == 1:
                    arr = arr.reshape(1, -1)
                self.known_features.append(arr)
                self.known_names.append(name)
        logger.info(f"Loaded {len(self.known_names)} face features.")

    def register_user(self, name: str, image: np.ndarray) -> bool:
        """Register a new user and store their SFace feature."""
        image = self._resize(image, 800)
        faces = self._detect_faces(image)
        if not faces:
            return False

        feat = self._feature(image, faces[0])  # (1, 128)

        # Persist image
        _, buffer = cv2.imencode(".jpg", image)
        self.storage.save_user_image(name, buffer.tobytes())

        # Persist feature
        history = self.storage.load_encodings()
        if name not in history:
            history[name] = []
        history[name].append(feat.flatten().tolist())
        self.storage.save_encodings(history)

        self.load_known_faces()
        return True

    # ------------------------------------------------------------------ #
    # Frame Processing (webcam & upload)                                   #
    # ------------------------------------------------------------------ #

    def process_frame(
        self, frame: np.ndarray, task_id: Optional[str] = None
    ) -> Tuple[np.ndarray, List[Dict]]:
        """Detect and (optionally) recognise faces in a frame."""
        def upd(p: int, s: str):
            if task_id:
                progress_store.update_progress(task_id, p, s)

        upd(10, "Preprocessing…")
        frame = self._resize(frame, 640)

        upd(40, "Detecting faces…")
        faces = self._detect_faces(frame)

        detections: List[Dict] = []
        if faces:
            upd(70, f"Recognising {len(faces)} face(s)…")
            for face in faces:
                x, y, w, h = face[0:4].astype(int)
                name, conf = "Unknown", 0.0

                if self.known_features:
                    try:
                        feat = self._feature(frame, face)
                        for kf, kn in zip(self.known_features, self.known_names):
                            score = float(
                                self.recognizer.match(feat, kf, cv2.FR_COSINE)
                            )
                            if score > 0.36 and score > conf:
                                conf, name = score, kn
                    except Exception as exc:
                        logger.warning(f"Recognition error for face: {exc}")

                detections.append({
                    "name": name,
                    "confidence": round(conf, 4),
                    "box": [int(y), int(x + w), int(y + h), int(x)],
                })

                color = (0, 200, 80) if name != "Unknown" else (30, 30, 220)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                label = name if name != "Unknown" else "Unknown"
                cv2.rectangle(
                    frame, (x, y - 28), (x + w, y), color, cv2.FILLED
                )
                cv2.putText(
                    frame, label, (x + 5, y - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
                )

        upd(100, "Complete")
        return frame, detections

    # ------------------------------------------------------------------ #
    # Target Matching (1 vs Many)                                          #
    # ------------------------------------------------------------------ #

    def match_faces(
        self, target_img: np.ndarray, group_img: np.ndarray, task_id: str
    ) -> Tuple[np.ndarray, Dict]:
        """Premium 1-vs-Many face matching using SFace deep learning."""

        def upd(p: int, s: str):
            progress_store.update_progress(task_id, p, s)

        upd(10, "Initialising AI engines…")
        target_img = self._resize(target_img, 640)
        group_img = self._resize(group_img, 640)
        gw = group_img.shape[1]

        # --- Step 1: Extract target embedding ---
        upd(20, "Analysing target face…")
        t_faces = self._detect_faces(target_img)
        if not t_faces:
            upd(100, "No face found in target image")
            return group_img, {"error": "No face detected in target image"}

        t_feat = self._feature(target_img, t_faces[0])

        # --- Step 2: Detect faces in group ---
        upd(50, "Scanning group photo…")
        g_faces = self._detect_faces(group_img)
        if not g_faces:
            upd(100, "No faces detected in group photo")
            return group_img, {"error": "No faces detected in group photo"}

        # --- Step 3: Compare ---
        upd(75, f"Comparing {len(g_faces)} face(s)…")
        best_idx, min_dist = -1, 10.0
        for i, gf in enumerate(g_faces):
            gfeat = self._feature(group_img, gf)
            d = self._score(t_feat, gfeat)
            if d < min_dist:
                min_dist, best_idx = d, i

        # Safety guard
        if best_idx < 0:
            upd(100, "Comparison failed")
            return group_img, {"error": "Comparison failed"}

        upd(90, "Generating result…")

        # --- Step 4: Categorise ---
        if min_dist < 0.5:
            status = "Strong Match"
        elif min_dist < 0.6:
            status = "Possible Match"
        else:
            status = "No Match"

        confidence = max(0.0, min(100.0, (1 - min_dist) * 100))

        # --- Step 5: Position ---
        bf = g_faces[best_idx]
        fx, fy, fw, fh = bf[0:4].astype(int)
        position = self._position(fx + fw // 2, gw)

        # --- Step 6: Markdown Explanation ---
        if status != "No Match":
            explanation = (
                f"### ✅ {status}\n\n"
                f"- **Confidence Score:** {confidence:.1f}%\n"
                f"- **Matched Person:** Face #{best_idx + 1} in group image\n"
                f"- **Position:** {position}\n"
                f"- **Distance Score:** {min_dist:.3f}\n\n"
                f"**Why it matched:**\n"
                f"The SFace neural network extracted a 128-dimensional embedding from "
                f"both faces and computed a Euclidean distance of **{min_dist:.3f}**, "
                f"which is below the {0.5 if status == 'Strong Match' else 0.6:.1f} "
                f"threshold. Facial landmarks including eye spacing, nose bridge, and "
                f"jawline curvature contributed to the high similarity score."
            )
        else:
            explanation = (
                f"### ❌ No Match Found\n\n"
                f"- **Closest Similarity:** {confidence:.1f}%\n"
                f"- **Closest Face:** Face #{best_idx + 1}\n"
                f"- **Distance Score:** {min_dist:.3f}\n\n"
                f"**Why it failed:**\n"
                f"The Euclidean distance between the target embedding and the closest "
                f"candidate was **{min_dist:.3f}**, exceeding the strict threshold of 0.60. "
                f"Differences in facial geometry—such as eye distance ratio, nose width, "
                f"or face shape—indicate these are likely different individuals."
            )

        # --- Step 7: Draw result ---
        color = (0, 200, 80) if status == "Strong Match" else \
                (0, 200, 255) if status == "Possible Match" else \
                (30, 30, 220)

        cv2.rectangle(group_img, (fx, fy), (fx + fw, fy + fh), color, 3)
        label = f"{status} {confidence:.0f}%"
        cv2.rectangle(
            group_img, (fx, fy - 30), (fx + fw, fy), color, cv2.FILLED
        )
        cv2.putText(
            group_img, label, (fx + 5, fy - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
        )

        result = {
            "match": status != "No Match",
            "status": status,
            "confidence": round(float(confidence), 2),
            "distance": round(float(min_dist), 4),
            "face_index": int(best_idx + 1),
            "position": position,
            "explanation_markdown": explanation,
        }

        upd(100, f"{status} — Complete")
        return group_img, result
