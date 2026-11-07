import pickle
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.face import FaceEncoding
from app.models.user import User
from app.schemas.user import FaceLogin, FaceRegister, TokenResponse, UserInfo, UserLogin, UserRegister
from app.services.face_service import face_service
from app.utils.auth import get_current_user

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


@router.get("/me", response_model=UserInfo)
def get_me(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="用户不存在或登录已失效，请重新登录",
        )
    return user


@router.post("/register/face")
def register_face(data: FaceRegister, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在，请先使用密码注册账号")

    image_bytes = face_service.decode_image(data.image_base64)
    if not face_service.save_face_sample(data.username, image_bytes, user.id):
        raise HTTPException(status_code=400, detail="未检测到清晰人脸，请调整光线后重试")

    features = face_service.extract_features(image_bytes)
    if features is None:
        raise HTTPException(status_code=400, detail="No face detected")

    existing = db.query(FaceEncoding).filter(FaceEncoding.user_id == user.id).first()
    if existing:
        existing.face_data = pickle.dumps(features)
        existing.updated_at = datetime.utcnow()
    else:
        db.add(FaceEncoding(user_id=user.id, face_data=pickle.dumps(features)))
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
    predicted_id, confidence = face_service.lbph_predict(image_bytes, user.id)
    print(
        f"face login: predicted={predicted_id} confidence={confidence} "
        f"expected={user.id} threshold={settings.face_match_threshold}"
    )

    matched = (
        predicted_id == user.id
        and confidence is not None
        and confidence < settings.face_match_threshold
    )

    if not matched and face_enc.face_data:
        live_features = face_service.extract_features(image_bytes)
        if live_features is not None:
            try:
                stored_features = pickle.loads(face_enc.face_data)
                ok, distance = face_service.compare_faces(
                    stored_features,
                    live_features,
                    threshold=settings.face_feature_threshold,
                )
                print(
                    f"face login fallback: distance={distance:.4f} "
                    f"threshold={settings.face_feature_threshold} ok={ok}"
                )
                matched = ok
            except Exception as exc:
                print(f"face login fallback error: {exc}")

    if not matched:
        score = f"（置信度 {confidence:.1f}）" if confidence is not None else ""
        raise HTTPException(
            status_code=400,
            detail=f"人脸不匹配{score}，请调整光线、正对镜头后重试，或使用密码登录",
        )

    token = create_token(user.id, user.username)
    return TokenResponse(access_token=token, username=user.username)
