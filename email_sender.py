import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

DEBUG_EMAIL = os.environ.get("DEBUG_EMAIL", "0") == "1"


def send_email(recipient: str, subject: str, html_body: str) -> None:
    if DEBUG_EMAIL:
        print("=== DEBUG EMAIL ===")
        print("TO:", recipient)
        print("SUBJECT:", subject)
        print("BODY:", html_body)
        print("===================")
        return

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("EMAIL_USER")
    pwd = os.environ.get("EMAIL_PWD")
    from_email = os.environ.get("EMAIL_FROM", user)

    msg = MIMEMultipart("alternative")
    msg["From"] = from_email
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    server = smtplib.SMTP(host, port)
    try:
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.sendmail(from_email, [recipient], msg.as_string())
        print(f"Successfully sent the mail to {recipient}")
    finally:
        server.quit()
