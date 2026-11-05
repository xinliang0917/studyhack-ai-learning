import io

import pickle

import numpy as np

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.user import User

from app.models.face import FaceEncoding

from app.schemas.user import UserRegister, UserLogin, TokenResponse, FaceRegister, FaceLogin

from app.services.face_service import face_service

import bcrypt

from jose import jwt

from app.config import settings



router = APIRouter(prefix="/api/auth", tags=["auth"])



def create_token(user_id: int, username: str) -> str:

    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)

    payload = {"sub": str(user_id), "username": username, "exp": expire}

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)



def get_password_hash(password: str) -> str:

    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()



def verify_password(password: str, hashed: str) -> bool:

    return bcrypt.checkpw(password.encode(), hashed.encode())



@router.post("/register/password", response_model=TokenResponse)

def register_password(data: UserRegister, db: Session = Depends(get_db)):

    if db.query(User).filter(User.username == data.username).first():

        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(username=data.username, password_hash=get_password_hash(data.password))

    db.add(user)

    db.commit()

    db.refresh(user)

    token = create_token(user.id, user.username)

    return TokenResponse(access_token=token, username=user.username)



@router.post("/login/password", response_model=TokenResponse)

def login_password(data: UserLogin, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.username == data.username).first()

    if not user or not verify_password(data.password, user.password_hash):

        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(user.id, user.username)

    return TokenResponse(access_token=token, username=user.username)



@router.post("/register/face")

def register_face(data: FaceRegister, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.username == data.username).first()

    if not user:

        raise HTTPException(status_code=404, detail="用户不存在，请先使用密码注册账号")

    image_bytes = face_service.decode_image(data.image_base64)
    face_service.save_face_sample(data.username, image_bytes, user.id)

    features = face_service.extract_features(image_bytes)

    if features is None:

        raise HTTPException(status_code=400, detail="No face detected")

    # Store features

    existing = db.query(FaceEncoding).filter(FaceEncoding.user_id == user.id).first()

    if existing:

        existing.face_data = pickle.dumps(features)

        existing.updated_at = datetime.utcnow()

    else:

        face_enc = FaceEncoding(user_id=user.id, face_data=pickle.dumps(features))

        db.add(face_enc)

    db.commit()

    return {"message": "Face registered successfully"}



@router.post("/login/face", response_model=TokenResponse)
def login_face(data: FaceLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    face_enc = db.query(FaceEncoding).filter(FaceEncoding.user_id == user.id).first()
    if not face_enc:
        raise HTTPException(status_code=400, detail="No face registered. Please register face first.")
    image_bytes = face_service.decode_image(data.image_base64)
    # LBPH-only approach (no fallback to lenient MediaPipe features)
    predicted_id, confidence = face_service.lbph_predict(image_bytes, user.id)
    if predicted_id is None:
        raise HTTPException(status_code=400, detail="人脸识别器未就绪，请先注册人脸")
    if predicted_id == user.id and confidence < 70:
        token = create_token(user.id, user.username)
        return TokenResponse(access_token=token, username=user.username)
    else:
        raise HTTPException(status_code=400, detail="人脸不匹配，请重试或使用密码登录")
@router.post("/register/password", response_model=TokenResponse)

def register_password(data: UserRegister, db: Session = Depends(get_db)):

    if db.query(User).filter(User.username == data.username).first():

        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(username=data.username, password_hash=get_password_hash(data.password))

    db.add(user)

    db.commit()

    db.refresh(user)

    token = create_token(user.id, user.username)

    return TokenResponse(access_token=token, username=user.username)



@router.post("/login/password", response_model=TokenResponse)

def login_password(data: UserLogin, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.username == data.username).first()

    if not user or not verify_password(data.password, user.password_hash):

        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(user.id, user.username)

    return TokenResponse(access_token=token, username=user.username)



@router.post("/register/face")

def register_face(data: FaceRegister, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.username == data.username).first()

    if not user:

        raise HTTPException(status_code=404, detail="用户不存在，请先使用密码注册账号")

    image_bytes = face_service.decode_image(data.image_base64)
    face_service.save_face_sample(data.username, image_bytes, user.id)

    features = face_service.extract_features(image_bytes)

    if features is None:

        raise HTTPException(status_code=400, detail="No face detected")

    # Store features

    existing = db.query(FaceEncoding).filter(FaceEncoding.user_id == user.id).first()

    if existing:

        existing.face_data = pickle.dumps(features)

        existing.updated_at = datetime.utcnow()

    else:

        face_enc = FaceEncoding(user_id=user.id, face_data=pickle.dumps(features))

        db.add(face_enc)

    db.commit()

    return {"message": "Face registered successfully"}



@router.post("/login/face", response_model=TokenResponse)

def login_face(data: FaceLogin, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.username == data.username).first()

    if not user:

        raise HTTPException(status_code=404, detail="User not found")

    face_enc = db.query(FaceEncoding).filter(FaceEncoding.user_id == user.id).first()

    if not face_enc:

        raise HTTPException(status_code=400, detail="No face registered. Please register face first.")

    image_bytes = face_service.decode_image(data.image_base64)
    features = face_service.extract_features(image_bytes)

    if features is None:

        raise HTTPException(status_code=400, detail="No face detected in image")

    stored_features = pickle.loads(face_enc.face_data)

    # Check for feature dimension mismatch (model upgrade)

    if len(features) != len(stored_features):

        # Delete old incompatible data and prompt user to re-register

        db.delete(face_enc)

        db.commit()

        raise HTTPException(status_code=400, detail="人脸识别模型已升级，请重新注册人脸")

    is_match, distance = face_service.compare_faces(features, stored_features)

    if not is_match:

       raise HTTPException(status_code=400, detail=f"人脸不匹配 (距离: {distance:.4f})，请重试或使用密码登录")

    token = create_token(user.id, user.username)

    return TokenResponse(access_token=token, username=user.username)

