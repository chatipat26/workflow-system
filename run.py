import uvicorn
import os

if __name__ == "__main__":
    # Support PORT or STREAMLIT_SERVER_PORT, defaulting to 8501 for Dokploy / Traefik
    port_str = os.environ.get("PORT") or os.environ.get("STREAMLIT_SERVER_PORT") or "8501"
    port = int(port_str)
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Team Workflow SVV on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False)
