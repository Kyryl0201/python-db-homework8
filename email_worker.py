import os
import time

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

import database
import models
import email_sender


BROKER_URL = os.environ.get("CELERY_BROKER_URL", "amqp://admin:admin@rabbitmq:5672//")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "rpc://")

app = Celery("tasks", broker=BROKER_URL, backend=RESULT_BACKEND)


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # каждый день в 09:00
    sender.add_periodic_task(
        crontab(hour=9, minute=0),
        send_daily_new_films.s(),
        name="daily_new_films_digest",
    )


@app.task(name="tasks.send_confirmation_email")
def send_confirmation_email(recipient_email: str, confirm_link: str):
    subject = "Подтверждение почты"
    html_body = f"""
    <h3>Подтверждение почты</h3>
    <p>Перейдите по ссылке, чтобы подтвердить email:</p>
    <p><a href="{confirm_link}">{confirm_link}</a></p>
    """
    email_sender.send_email(recipient_email, subject, html_body)
    return f"confirmation email sent to {recipient_email}"


@app.task(name="tasks.send_daily_new_films")
def send_daily_new_films():
    session = database.db_session

    now_ts = int(time.time())
    since_ts = now_ts - 24 * 60 * 60

    newest_films = session.execute(
        select(models.Film).where(models.Film.added_at >= since_ts).order_by(models.Film.added_at.desc())
    ).scalars().all()

    if not newest_films:
        print("No new films for last 24h, skip.")
        return "no new films"

    recipients = session.execute(
        select(models.User.email).where(models.User.email.is_not(None))
    ).scalars().all()

    if not recipients:
        print("No recipients, skip.")
        return "no recipients"

    subject = "Новые фильмы за последние 24 часа"
    html_body = email_sender.render_email_template(newest_films)

    sent = 0
    for email in recipients:
        # лучше отправлять отдельными задачами, чтобы не завалить один процесс
        send_html_email.delay(email, subject, html_body)
        sent += 1

    return f"queued {sent} emails"


@app.task(name="tasks.send_html_email")
def send_html_email(recipient_email: str, subject: str, html_body: str):
    email_sender.send_email(recipient_email, subject, html_body)
    return f"sent to {recipient_email}"

