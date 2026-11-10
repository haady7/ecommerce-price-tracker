import smtplib
from email.message import EmailMessage
from flask import current_app

def send_price_alert(to_email, product_name, product_url, price, target):
    cfg = current_app.config
    if not all([cfg["SMTP_HOST"], cfg["SMTP_USERNAME"], cfg["SMTP_PASSWORD"], cfg["SMTP_FROM"]]):
        raise RuntimeError("SMTP is not configured. Set SMTP credentials in the .env file.")
    message = EmailMessage()
    message["Subject"] = f"Price drop alert: {product_name}"
    message["From"] = cfg["SMTP_FROM"]
    message["To"] = to_email
    message.set_content(
        f"Good news! The tracked product has reached your target price.\\n\\n"
        f"Product: {product_name}\\nCurrent price: ₹{price:,.2f}\\n"
        f"Your target: ₹{target:,.2f}\\nProduct link: {product_url}\\n"
    )
    with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=20) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(cfg["SMTP_USERNAME"], cfg["SMTP_PASSWORD"])
        server.send_message(message)
