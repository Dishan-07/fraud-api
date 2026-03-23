# ============================================================
# email_service.py — Send emails using Gmail SMTP
# Welcome email, OTP email, password reset confirmation
# ============================================================
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os

load_dotenv()

MAIL_USERNAME  = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD  = os.getenv("MAIL_PASSWORD")
MAIL_FROM      = os.getenv("MAIL_FROM")
MAIL_SERVER    = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT      = int(os.getenv("MAIL_PORT", 587))
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "FraudShield AI")


def generate_otp() -> str:
    """Generate a 6-digit OTP code."""
    return ''.join(random.choices(string.digits, k=6))


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send an email via Gmail SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_welcome_email(to_email: str, full_name: str) -> bool:
    """Send welcome email after first login/registration."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #050914; color: #F1F5F9; padding: 40px;">
      <div style="max-width: 600px; margin: 0 auto; background: #0D1526;
                  border-radius: 16px; padding: 40px;
                  border: 1px solid #1E3A5F;">
        <div style="text-align: center; margin-bottom: 30px;">
          <h1 style="color: #0EA5E9; font-size: 28px;">🛡️ FraudShield AI</h1>
          <p style="color: #64748B; font-size: 14px;">Powered by PSO + KAN Neural Network</p>
        </div>
        <h2 style="color: #F1F5F9;">Welcome, {full_name}! 👋</h2>
        <p style="color: #94A3B8; line-height: 1.6;">
          You have successfully joined <strong style="color: #0EA5E9;">FraudShield AI</strong> —
          the most advanced credit card fraud detection system powered by
          <strong>Kolmogorov-Arnold Networks (KAN)</strong> and
          <strong>Particle Swarm Optimization (PSO)</strong>.
        </p>
        <div style="background: #0A1628; border-radius: 12px; padding: 20px;
                    margin: 20px 0; border-left: 4px solid #0EA5E9;">
          <h3 style="color: #0EA5E9; margin: 0 0 10px 0;">Your Model Stats:</h3>
          <p style="color: #94A3B8; margin: 4px 0;">🎯 ROC-AUC Score: <strong style="color: #10B981;">0.9766</strong></p>
          <p style="color: #94A3B8; margin: 4px 0;">📊 Recall Rate: <strong style="color: #10B981;">81.68%</strong></p>
          <p style="color: #94A3B8; margin: 4px 0;">🧠 Neural Network: <strong style="color: #10B981;">KAN (MIT 2024)</strong></p>
          <p style="color: #94A3B8; margin: 4px 0;">⚡ Optimizer: <strong style="color: #10B981;">PSO (10 iterations)</strong></p>
        </div>
        <p style="color: #94A3B8;">
          Start analyzing transactions now and protect your finances
          with state-of-the-art AI fraud detection.
        </p>
        <div style="text-align: center; margin-top: 30px;">
          <a href="http://localhost:5173" style="background: linear-gradient(135deg, #0EA5E9, #06B6D4);
             color: white; padding: 14px 32px; border-radius: 8px;
             text-decoration: none; font-weight: bold; font-size: 16px;">
            Go to Dashboard →
          </a>
        </div>
        <hr style="border: 1px solid #1E3A5F; margin: 30px 0;">
        <p style="color: #475569; font-size: 12px; text-align: center;">
          FraudShield AI — Advanced Fraud Detection System<br>
          Powered by PSO + KAN Neural Network
        </p>
      </div>
    </body>
    </html>
    """
    return send_email(to_email, "🛡️ Welcome to FraudShield AI!", html)


def send_otp_email(to_email: str, otp_code: str, full_name: str = "User") -> bool:
    """Send OTP code for password reset."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #050914; color: #F1F5F9; padding: 40px;">
      <div style="max-width: 600px; margin: 0 auto; background: #0D1526;
                  border-radius: 16px; padding: 40px;
                  border: 1px solid #1E3A5F;">
        <div style="text-align: center; margin-bottom: 30px;">
          <h1 style="color: #0EA5E9;">🛡️ FraudShield AI</h1>
        </div>
        <h2 style="color: #F1F5F9;">Password Reset Request 🔐</h2>
        <p style="color: #94A3B8;">Hi {full_name},</p>
        <p style="color: #94A3B8; line-height: 1.6;">
          We received a request to reset your password.
          Use the OTP code below to proceed:
        </p>
        <div style="text-align: center; margin: 30px 0;">
          <div style="background: #0A1628; border-radius: 12px; padding: 30px;
                      border: 2px solid #0EA5E9; display: inline-block;">
            <p style="color: #64748B; font-size: 14px; margin: 0 0 10px 0;">
              Your OTP Code
            </p>
            <h1 style="color: #0EA5E9; font-size: 48px; letter-spacing: 16px;
                       font-family: monospace; margin: 0;">
              {otp_code}
            </h1>
            <p style="color: #EF4444; font-size: 12px; margin: 10px 0 0 0;">
              ⏰ Expires in 10 minutes
            </p>
          </div>
        </div>
        <p style="color: #94A3B8; line-height: 1.6;">
          If you did not request a password reset, please ignore this email.
          Your account remains secure.
        </p>
        <hr style="border: 1px solid #1E3A5F; margin: 30px 0;">
        <p style="color: #475569; font-size: 12px; text-align: center;">
          FraudShield AI — This OTP expires in 10 minutes
        </p>
      </div>
    </body>
    </html>
    """
    return send_email(to_email, "🔐 FraudShield AI — Password Reset OTP", html)


def send_password_changed_email(to_email: str, full_name: str = "User") -> bool:
    """Send confirmation after password is successfully changed."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #050914; color: #F1F5F9; padding: 40px;">
      <div style="max-width: 600px; margin: 0 auto; background: #0D1526;
                  border-radius: 16px; padding: 40px; border: 1px solid #1E3A5F;">
        <h1 style="color: #0EA5E9; text-align: center;">🛡️ FraudShield AI</h1>
        <h2 style="color: #10B981;">✅ Password Changed Successfully</h2>
        <p style="color: #94A3B8;">Hi {full_name},</p>
        <p style="color: #94A3B8; line-height: 1.6;">
          Your password has been successfully updated.
          You can now log in with your new password.
        </p>
        <div style="background: #0A1628; border-radius: 12px; padding: 20px;
                    border-left: 4px solid #EF4444; margin: 20px 0;">
          <p style="color: #EF4444; margin: 0;">
            ⚠️ If you did not make this change, contact support immediately.
          </p>
        </div>
        <hr style="border: 1px solid #1E3A5F; margin: 30px 0;">
        <p style="color: #475569; font-size: 12px; text-align: center;">
          FraudShield AI Security Team
        </p>
      </div>
    </body>
    </html>
    """
    return send_email(to_email, "✅ FraudShield AI — Password Changed", html)
