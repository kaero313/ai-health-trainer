import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

PASSWORD_PATTERN = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z\d]).{8,}$"
PASSWORD_PATTERN_COMPILED = re.compile(PASSWORD_PATTERN)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    password_confirm: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        normalized = value.lower()
        if len(normalized) > 255:
            raise ValueError("Email must be 255 characters or less")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if PASSWORD_PATTERN_COMPILED.fullmatch(value) is None:
            raise ValueError("Password must include letters, numbers, and special characters")
        return value

    @model_validator(mode="after")
    def validate_password_match(self) -> "RegisterRequest":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        normalized = value.lower()
        if len(normalized) > 255:
            raise ValueError("Email must be 255 characters or less")
        return normalized


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class AuthUserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime


class RegisterResponseData(BaseModel):
    user: AuthUserResponse
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]


class LoginResponseData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
    expires_in: int


class RefreshResponseData(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int


class RegisterResponse(BaseModel):
    status: Literal["success"] = "success"
    data: RegisterResponseData
    message: str | None = None


class LoginResponse(BaseModel):
    status: Literal["success"] = "success"
    data: LoginResponseData
    message: str | None = None


class RefreshResponse(BaseModel):
    status: Literal["success"] = "success"
    data: RefreshResponseData
    message: str | None = None
