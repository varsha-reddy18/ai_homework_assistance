from fastapi import APIRouter, HTTPException
from models.auth_models import SignupRequest, LoginRequest
from services.supabase_client import supabase

router = APIRouter()

@router.post("/signup")
async def signup(user: SignupRequest):

    try:
        response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })

        if response.user is None:
            raise HTTPException(status_code=400, detail="Signup failed")

        return {
            "message": "Signup successful. Please verify your email if required.",
            "user": response.user
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/login")
async def login(user: LoginRequest):

    try:
        response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })

        if response.session is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        return {
            "message": "Login successful",
            "access_token": response.session.access_token,
            "user": response.user
        }

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")