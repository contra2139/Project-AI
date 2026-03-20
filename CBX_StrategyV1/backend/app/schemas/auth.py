from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenData(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class LoginResponse(BaseModel):
    success: bool
    data: TokenData

class UserData(BaseModel):
    user_id: str
    username: str
    role: str

class UserInfo(BaseModel):
    success: bool
    data: UserData
