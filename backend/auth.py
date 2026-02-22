# app/schemas/auth.py
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: str
    employee_code: str
    full_name: str
    email: str
    role: str
    department_name: str | None = None
    is_enrolled: bool

    model_config = {"from_attributes": True}
