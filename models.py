# ============================================================
# models.py — SQLAlchemy database table definitions
# ============================================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    """Users table — stores registered users."""
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    full_name       = Column(String(100), nullable=False)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active       = Column(Boolean, default=True)
    is_verified     = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    last_login      = Column(DateTime(timezone=True), nullable=True)


class OTPCode(Base):
    """OTP codes table — stores password reset OTPs."""
    __tablename__ = "otp_codes"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String(255), index=True, nullable=False)
    otp_code   = Column(String(6), nullable=False)
    is_used    = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PredictionLog(Base):
    """Prediction logs — stores every fraud detection result."""
    __tablename__ = "prediction_logs"

    id                 = Column(Integer, primary_key=True, index=True)
    user_id            = Column(Integer, nullable=True)
    transaction_amount = Column(Float, nullable=False)
    merchant_name      = Column(String(255), nullable=True)
    category           = Column(String(100), nullable=True)
    trans_hour         = Column(Integer, nullable=True)
    distance_km        = Column(Float, nullable=True)
    fraud_probability  = Column(Float, nullable=False)
    prediction         = Column(String(10), nullable=False)  # FRAUD or SAFE
    threshold_used     = Column(Float, nullable=False)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
