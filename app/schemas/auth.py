"""Authentication schemas"""
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str
    remember: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
