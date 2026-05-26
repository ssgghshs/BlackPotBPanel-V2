from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class UserBase(BaseModel):
    username: str
    email: str


class RoleEnum(str, Enum):
    ADMIN = "admin"
    AUDITOR = "auditor"
    OPERATOR = "operator"


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: RoleEnum = RoleEnum.OPERATOR


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[RoleEnum] = None


class UserInDB(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    is_active: int
    role: RoleEnum
    
    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    pass


class UserLogin(BaseModel):
    username: str
    password: str
    captcha: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class TokenWithDefaultPasswordCheck(Token):
    is_default_password: bool


class CaptchaResponse(BaseModel):
    captcha_id: str
    captcha_image: str