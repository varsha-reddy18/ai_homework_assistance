from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

# =========================
# IMPORT YOUR ROUTERS
# =========================
from routes.auth_routes import router as auth_router
from routes.ask_routes import router as ask_router
from routes.image_routes import router as image_router
from routes.grammar_routes import router as grammar_router

app = FastAPI()

# =========================
# CORS (safe for frontend requests)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # for deployment/testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# PATHS
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "../frontend"))

# =========================
# SERVE STATIC FILES
# =========================
# This serves:
# /static/css/...
# /static/js/...
# /static/images/...
# /static/login.html etc.
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# =========================
# INCLUDE API ROUTES
# =========================
app.include_router(auth_router)
app.include_router(ask_router)
app.include_router(image_router)
app.include_router(grammar_router)

# =========================
# PAGE ROUTES
# =========================
@app.get("/")
def home():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/login-page")
def login_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

@app.get("/signup-page")
def signup_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "signup.html"))

@app.get("/dashboard")
def dashboard_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

# Optional direct routes for static HTML files if needed
@app.get("/login.html")
def login_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

@app.get("/signup.html")
def signup_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "signup.html"))

@app.get("/dashboard.html")
def dashboard_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

# =========================
# HEALTH CHECK
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}