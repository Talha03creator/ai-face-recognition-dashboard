from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .routes import detection, users, logs
import os

app = FastAPI(title="Face Recognition Dashboard")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(detection.router, prefix="/api/detect", tags=["Detection"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])

# Serve Frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
