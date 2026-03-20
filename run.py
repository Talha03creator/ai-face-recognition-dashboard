import uvicorn
import os
import sys

if __name__ == "__main__":
    # Ensure data directory exists
    data_dir = os.path.join(os.getcwd(), "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.makedirs(os.path.join(data_dir, "users"))
        print(f"Created data directory at {data_dir}")

    print("Starting Face Recognition Dashboard...")
    print("Point your browser to http://localhost:8000")
    
    try:
        uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
    except Exception as e:
        print(f"Error starting server: {e}")
        input("Press Enter to exit...")
