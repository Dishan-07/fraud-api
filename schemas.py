# ============================================================
# schemas.py — Pydantic models for request/response validation
# ============================================================
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── AUTH SCHEMAS ─────────────────────────────────────────────
class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# ── PASSWORD RESET SCHEMAS ────────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str


# ── PREDICTION SCHEMAS ────────────────────────────────────────
class TransactionInput(BaseModel):
    # All fields matching PSO_KAN_fast.py features
    amt:           float
    merchant:      Optional[str] = "unknown"
    category:      Optional[str] = "misc_net"
    cc_num:        Optional[float] = 0.0
    gender:        Optional[str] = "M"
    city_pop:      Optional[float] = 100000.0
    job:           Optional[str] = "unknown"
    trans_hour:    Optional[int] = 12
    trans_day:     Optional[int] = 0
    trans_month:   Optional[int] = 1
    trans_year:    Optional[int] = 2024
    lat:           Optional[float] = 0.0
    long:          Optional[float] = 0.0
    merch_lat:     Optional[float] = 0.0
    merch_long:    Optional[float] = 0.0
    distance_km:   Optional[float] = None   # auto-calculated if None
    is_night:      Optional[int] = None      # auto from trans_hour if None
    is_weekend:    Optional[int] = None      # auto from trans_day if None


class PredictionResponse(BaseModel):
    fraud_probability: float
    prediction:        str       # "FRAUD" or "SAFE"
    confidence:        str       # "HIGH", "MEDIUM", "LOW"
    threshold:         float
    risk_level:        str       # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    risk_factors: dict
