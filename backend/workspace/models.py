from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


class AccountApplication(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)
    two_factor_secret: str | None = Field(default=None, min_length=16, max_length=64)
    two_factor_code: str | None = Field(default=None, pattern=r"^\d{6}$")

    @model_validator(mode="after")
    def validate_two_factor_fields(self) -> "AccountApplication":
        if bool(self.two_factor_secret) != bool(self.two_factor_code):
            raise ValueError("Two-factor secret and verification code must be provided together")
        return self


class TwoFactorSetupRequest(BaseModel):
    email: EmailStr


class LoginCredentials(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)
    two_factor_code: str | None = Field(default=None, pattern=r"^\d{6}$")


class RoleUpdate(BaseModel):
    role: Literal["Worker", "Medlem", "Admin"]


class MaterialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sku: str = Field(min_length=1, max_length=40)
    category: Literal["Förbrukning", "Elektronik", "Utrustning"]
    warehouse: str = Field(min_length=1, max_length=120)
    section: str = Field(min_length=1, max_length=120)
    quantity: int = Field(ge=0)
    unit: str = Field(min_length=1, max_length=20)
    damaged_count: int = Field(default=0, ge=0)


class ShipmentCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    customer_email: EmailStr | None = None
    material_id: str = Field(min_length=1)
    quantity: int = Field(ge=1)


class ShipmentStatusUpdate(BaseModel):
    status: Literal["delivered", "cancelled"]


class ApplicationResponse(BaseModel):
    name: str
    email: EmailStr
    id: str
    status: str
    submitted_at: datetime
