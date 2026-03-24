from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import ask_routes, image_routes,grammar_routes,auth_routes

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(ask_routes.router)
app.include_router(image_routes.router)
app.include_router(grammar_routes.router)