import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Fill these in
EMAIL    = "dishanchakraborty30@gmail.com"
PASSWORD = "abzwssjxggcoidye"   # no spaces!
TO_EMAIL = "dishanchakraborty07@gmail.com"

try:
    msg = MIMEMultipart()
    msg["Subject"] = "FraudShield Test Email"
    msg["From"]    = EMAIL
    msg["To"]      = TO_EMAIL
    msg.attach(MIMEText("<h1>Test email working!</h1>", "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, TO_EMAIL, msg.as_string())

    print("✅ Email sent successfully!")
except Exception as e:
    print(f"❌ Error: {e}")