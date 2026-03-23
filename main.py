# ============================================================
# main.py — FastAPI main application
# FIXED: CORS preflight OPTIONS requests handled properly
# ============================================================
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from database import engine, get_db, Base
from models import User, OTPCode, PredictionLog
from schemas import (
    UserRegister, UserLogin, TokenResponse, UserResponse,
    ForgotPasswordRequest, VerifyOTPRequest, ResetPasswordRequest,
    TransactionInput, PredictionResponse
)
from auth import (
    hash_password, verify_password,
    create_access_token, get_current_user
)
from email_service import (
    generate_otp, send_welcome_email,
    send_otp_email, send_password_changed_email
)
from kan_predictor import predictor

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FraudShield AI API",
    description="Credit Card Fraud Detection using PSO + KAN",
    version="1.0.0"
)

# ── FIXED CORS — allows all origins during development ──────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Allow all origins
    allow_credentials=False,       # Must be False when allow_origins=["*"]
    allow_methods=["*"],           # Allow all methods including OPTIONS
    allow_headers=["*"],           # Allow all headers
    expose_headers=["*"],
)

# ── Handle OPTIONS preflight explicitly ──────────────────────
@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


# ══════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════

@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        is_verified=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    try:
        sent = send_welcome_email(new_user.email, new_user.full_name)
        if sent:
            print(f"✅ Welcome email sent to {new_user.email}")
        else:
            print(f"⚠️  Welcome email failed for {new_user.email}")
    except Exception as e:
        print(f"⚠️  Email error: {e}")

    return new_user


@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is deactivated")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ══════════════════════════════════════════════════════════════
# PASSWORD RESET
# ══════════════════════════════════════════════════════════════

@app.post("/auth/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        return {"message": "If this email exists, an OTP has been sent."}

    db.query(OTPCode).filter(
        OTPCode.email == request.email,
        OTPCode.is_used == False
    ).delete()
    db.commit()

    otp = generate_otp()
    otp_record = OTPCode(
        email=request.email,
        otp_code=otp,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    db.add(otp_record)
    db.commit()

    try:
        send_otp_email(request.email, otp, user.full_name)
        print(f"✅ OTP sent to {request.email}: {otp}")
    except Exception as e:
        print(f"⚠️  OTP email failed: {e}")
        return {"message": "OTP generated", "debug_otp": otp}

    return {"message": "OTP sent to your email. Valid for 10 minutes."}


@app.post("/auth/verify-otp")
def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    otp_record = db.query(OTPCode).filter(
        OTPCode.email    == request.email,
        OTPCode.otp_code == request.otp_code,
        OTPCode.is_used  == False
    ).first()
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP code")
    if datetime.now(timezone.utc) > otp_record.expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired")
    return {"message": "OTP verified successfully", "valid": True}


@app.post("/auth/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    otp_record = db.query(OTPCode).filter(
        OTPCode.email    == request.email,
        OTPCode.otp_code == request.otp_code,
        OTPCode.is_used  == False
    ).first()
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or already used OTP")
    if datetime.now(timezone.utc) > otp_record.expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired")
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(request.new_password)
    otp_record.is_used   = True
    db.commit()

    try:
        send_password_changed_email(request.email, user.full_name)
    except Exception as e:
        print(f"⚠️  Password changed email failed: {e}")

    return {"message": "Password reset successfully. You can now log in."}


# ══════════════════════════════════════════════════════════════
# PREDICTION
# ══════════════════════════════════════════════════════════════

@app.post("/predict", response_model=PredictionResponse)
def predict(
    transaction: TransactionInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = predictor.predict(transaction.model_dump())

    log = PredictionLog(
        user_id=current_user.id,
        transaction_amount=transaction.amt,
        merchant_name=transaction.merchant,
        category=transaction.category,
        trans_hour=transaction.trans_hour,
        distance_km=transaction.distance_km,
        fraud_probability=result["fraud_probability"],
        prediction=result["prediction"],
        threshold_used=result["threshold"]
    )
    db.add(log)
    db.commit()

    return result


@app.get("/predictions/history")
def get_prediction_history(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logs = db.query(PredictionLog).filter(
        PredictionLog.user_id == current_user.id
    ).order_by(PredictionLog.created_at.desc()).limit(limit).all()
    return logs


# ══════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "status": "online",
        "app": "FraudShield AI API",
        "model": "PSO + KAN Neural Network",
        "version": "1.0.0",
        "model_loaded": predictor.is_loaded
    }

@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": predictor.is_loaded}