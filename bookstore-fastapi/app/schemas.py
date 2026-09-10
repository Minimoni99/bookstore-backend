from pydantic import BaseModel, EmailStr
from typing import Optional, List


class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    name: str
    country: str


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    currentPassword: str
    newPassword: str


class BookCreate(BaseModel):
    title: str
    penName: Optional[str] = ""
    priceCents: int
    description: Optional[str] = ""
    coverUrl: Optional[str] = ""
    downloadUrl: str


class BookUpdate(BaseModel):
    title: Optional[str] = None
    penName: Optional[str] = None
    priceCents: Optional[int] = None
    description: Optional[str] = None
    coverUrl: Optional[str] = None
    downloadUrl: Optional[str] = None


class RoleUpdate(BaseModel):
    role: str


class SettingsUpdate(BaseModel):
    penName: Optional[str] = None
    heroHeadline: Optional[str] = None
    heroSubheadline: Optional[str] = None
    heroVideoUrl: Optional[str] = None
    authorPhotoUrl: Optional[str] = None
    authorBio: Optional[str] = None
    contactEmail: Optional[str] = None
    whatsappLink: Optional[str] = None
    telegramLink: Optional[str] = None
    subscriptionPriceLabel: Optional[str] = None
    subscriptionCtaText: Optional[str] = None
    subscriptionBenefitsRegular: Optional[List[str]] = None
    subscriptionBenefitsPremium: Optional[List[str]] = None
