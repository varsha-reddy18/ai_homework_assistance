from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))

app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def home():
    return FileResponse(os.path.join(frontend_path, "index.html"))