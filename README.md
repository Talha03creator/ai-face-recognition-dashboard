# 👁 FaceAI — AI Face Detection & Recognition Dashboard

A production-quality, fully local Face Detection and Recognition web application built with **FastAPI**, **OpenCV**, and **SFace deep learning**. No external APIs. All processing happens on-device.

---

## ✨ Features

- **Live Webcam Detection** — Real-time face detection from your webcam with bounding boxes
- **Image Upload Detection** — Upload any photo; progress bar tracks each processing step
- **1-vs-Many Target Matching** — Upload a target face and a group photo; the AI finds the match
- **Distance-Based Matching** — Strict thresholds using Euclidean distance:
  - `< 0.5` → Strong Match ✅
  - `0.5 – 0.6` → Possible Match ⚠️
  - `> 0.6` → No Match ❌
- **Explainable AI Results** — Detailed Markdown explanation for every match result
- **Confidence Scoring** — `confidence = (1 - distance) * 100`
- **Spatial Identification** — Detects face position (Left / Center / Right) in group photos
- **User Registration** — Register known faces with SFace embeddings stored locally
- **Detection Logs** — Full timestamped history of all detections
- **Async Processing** — Non-blocking background tasks with real-time progress polling
- **Clean Dashboard UI** — Professional white-theme dashboard with sidebar navigation

---

## 🗂 Project Structure

```
Face Detection & Recognition/
├── backend/
│   ├── main.py                  # FastAPI app setup & routing
│   ├── routes/
│   │   ├── detection.py         # Upload, match, webcam endpoints
│   │   ├── users.py             # User registration & management
│   │   └── logs.py              # Detection log endpoints
│   ├── services/
│   │   ├── face_service.py      # AI core: YuNet + SFace engine
│   │   ├── storage_service.py   # Local file storage
│   │   └── progress_store.py    # Async task progress tracking
│   └── utils/
│       └── logger.py            # Detection event logger
├── frontend/
│   ├── index.html               # App shell + view templates
│   ├── assets/
│   │   └── styles.css           # Clean professional UI styles
│   └── js/
│       ├── api.js               # Backend API wrapper
│       └── app.js               # View logic & state management
├── models/                      # ONNX models (downloaded separately)
│   ├── face_detection_yunet.onnx
│   └── face_recognition_sface.onnx
├── data/                        # Auto-created at runtime
│   ├── users/                   # Registered face images
│   └── encodings.pkl            # SFace feature embeddings
├── run.py                       # App entry point
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Talha03creator/ai-face-recognition-dashboard.git
cd ai-face-recognition-dashboard
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> ✅ No `dlib` or `cmake` required. Uses OpenCV's built-in AI engines.

### 4. Download AI Models

The ONNX models are not included in the repository (large binary files).
Download them by running:

```bash
python download_models.py
```

This downloads:
- `models/face_detection_yunet.onnx` (~227 KB)
- `models/face_recognition_sface.onnx` (~37 MB)

### 5. Configure Environment (Optional)

```bash
cp .env.example .env
# Edit .env if needed (default values work out of the box)
```

---

## 🚀 Usage

### Start the Server

```bash
python run.py
```

Open your browser at **http://localhost:8000**

### Pages

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Stats, engine status, recent activity |
| Detect Faces | Sidebar | Webcam + image upload detection |
| Face Match | Sidebar | 1-vs-Many target matching |
| Users | Sidebar | Register and manage known faces |
| Logs | Sidebar | Full detection history |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/detect/upload` | Upload image for async detection |
| `POST` | `/api/detect/match` | Upload target + group for matching |
| `GET`  | `/api/detect/progress/{task_id}` | Poll task progress |
| `GET`  | `/api/detect/result/{task_id}` | Fetch completed result |
| `GET`  | `/api/detect/video_feed` | Webcam MJPEG stream |
| `GET`  | `/api/users/` | List registered users |
| `POST` | `/api/users/register` | Register a new user |
| `DELETE` | `/api/users/{name}` | Delete a user |
| `GET`  | `/api/logs/` | Fetch detection logs |

---

## 📸 Screenshots

> Dashboard with live stats and recent activity feed

![Dashboard UI](https://raw.githubusercontent.com/Talha03creator/ai-face-recognition-dashboard/main/docs/dashboard.png)

---

## 📋 Recommendations

- Use GPU if available for significantly faster inference (configure OpenCV DNN backend).
- Keep uploaded images under 1 MB for optimal processing speed.
- Precompute face encodings for all registered users before high-load sessions.
- Avoid uploading images with multiple overlapping faces in profile photos.
- Use clear, well-lit, front-facing photos for registration to improve recognition accuracy.
- Ensure Python 3.10+ for best compatibility with FastAPI and OpenCV.
- For group photos with many faces (10+), increase the image resolution limit beyond 640px.
- Regularly back up `data/encodings.pkl` — it stores all registered face features.

---

## 🛡 Security

- All processing is fully **local** — no data is sent to external servers.
- `.env` file is excluded from git via `.gitignore`.
- User face data is stored only in the local `data/` directory.

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn |
| AI Engine | OpenCV YuNet + SFace (ONNX) |
| Storage | Local filesystem + Pickle |
| Frontend | HTML5 + Vanilla CSS + JavaScript |
| Font | Inter (Google Fonts) |

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

*Built with ❤️ using Python, FastAPI, and OpenCV*
