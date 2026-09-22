from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class AccountApplication(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)


class LoginCredentials(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class RoleUpdate(BaseModel):
    role: Literal["Medlem", "Admin"]


class ApplicationResponse(BaseModel):
    name: str
    email: EmailStr
    id: str
    status: str
    submitted_at: datetime
