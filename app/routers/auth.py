from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.services.auth import hash_password, authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=201)
def register(username: str, email: str, password: str, db: Session = Depends(get_db)):
    """
    Create a new user account.
    Passwords are stored as bcrypt hashes - never plain text.
    """
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "Username already taken")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email already registered")

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "email": user.email}


@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login with username and password.
    Returns a JWT Bearer token to use in future requests.
    OAuth2PasswordRequestForm expects form data (not JSON) with
    fields: username and password.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
