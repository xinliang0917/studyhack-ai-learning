from pydantic import BaseModel

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class FaceRegister(BaseModel):
    username: str
    image_base64: str

class FaceLogin(BaseModel):
    username: str
    image_base64: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

class UserInfo(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True
