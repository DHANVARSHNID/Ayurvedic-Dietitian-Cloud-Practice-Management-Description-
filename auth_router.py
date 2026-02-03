from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.auth_schema import UserCreate, UserOut, LoginSchema
from app.database import get_db
from app.utils.hashing import Hasher
from app.utils.jwt import create_access_token

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


# ------------------------------
# REGISTER USER
# ------------------------------
@auth_router.post("/register", response_model=UserOut)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        name=user.name,
        email=user.email,
        password=Hasher.hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ------------------------------
# LOGIN USER
# ------------------------------
@auth_router.post("/login")
async def login_user(credentials: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email")

    if not Hasher.verify_password(credentials.password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect password")

    # create JWT access token
    token = create_access_token({"user_id": user.id})

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer"
    }
