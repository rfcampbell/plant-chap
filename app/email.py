"""
Email utility for Plant Chap using stdlib smtplib
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


def send_email(to, subject, body):
    """Send an email using SMTP with TLS."""
    config = current_app.config
    sender = config.get('MAIL_DEFAULT_SENDER') or config.get('MAIL_USERNAME')

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(config['MAIL_SERVER'], config['MAIL_PORT'])
        if config.get('MAIL_USE_TLS'):
            server.starttls()
        username = config.get('MAIL_USERNAME')
        password = config.get('MAIL_PASSWORD')
        if username and password:
            server.login(username, password)
        server.sendmail(sender, to, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        current_app.logger.error(f'Failed to send email to {to}: {e}')
        return False
