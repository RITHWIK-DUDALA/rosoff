import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
import uvicorn

if __name__ == "__main__":
    print("[PROJECT W.A.L.L.] Starting uvicorn on 0.0.0.0:8000...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
