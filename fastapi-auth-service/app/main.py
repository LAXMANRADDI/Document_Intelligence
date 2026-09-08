from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas, crud, security
from .database import engine, Base
from .deps import get_db, get_current_user

app = FastAPI(title="Auth Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/signup", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(db, payload.email, payload.password)
    return user


@app.post("/auth/login", response_model=schemas.TokenPair)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, payload.email)
    if not user or not security.verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    access_token = security.create_access_token(subject=user.email)
    refresh_token, expires_at = security.create_refresh_token(subject=user.email)
    crud.store_refresh_token(db, user.id, refresh_token, expires_at)
    return schemas.TokenPair(access_token=access_token, refresh_token=refresh_token)


@app.post("/auth/refresh", response_model=schemas.AccessToken)
def refresh(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    token_record = crud.get_refresh_token(db, payload.refresh_token)
    if not token_record or token_record.revoked:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    decoded = security.decode_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = security.create_access_token(subject=decoded["sub"])
    return schemas.AccessToken(access_token=access_token)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    token_record = crud.get_refresh_token(db, payload.refresh_token)
    if token_record:
        crud.revoke_refresh_token(db, token_record)
    return


@app.get("/auth/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
