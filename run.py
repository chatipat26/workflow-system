import uvicorn
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Team Workflow SVV on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False)
