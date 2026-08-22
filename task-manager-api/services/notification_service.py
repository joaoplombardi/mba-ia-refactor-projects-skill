"""Email notifications, behind an interface the composition root can swap.

The legacy version hardcoded SMTP credentials in its constructor, opened a
blocking connection on the request path, and kept notifications in an in-process
list. It was also never imported by any route.
"""
import logging
import smtplib

from utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class SmtpEmailClient:
    """Real client. Credentials come from config, never from a literal."""

    def __init__(self, host, port, user, password, timeout=10):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.timeout = timeout

    def send(self, to, subject, body):
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, to, f"Subject: {subject}\n\n{body}")
            logger.info("Email enviado para %s", to)
            return True
        except OSError as error:
            logger.error("Falha ao enviar email para %s: %s", to, error)
            return False


class NullEmailClient:
    """Default in development and tests: no network, no credentials needed."""

    def send(self, to, subject, body):
        logger.info("Email suprimido (to=%s, subject=%s)", to, subject)
        return True


class NotificationService:
    def __init__(self, email_client):
        self.email_client = email_client

    def notify_task_assigned(self, user, task):
        self.email_client.send(
            user.email,
            f"Nova task atribuída: {task.title}",
            f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
            f"Prioridade: {task.priority}\nStatus: {task.status}",
        )
        logger.info(
            "Notificação task_assigned (user=%s, task=%s, em=%s)",
            user.id,
            task.id,
            utc_now(),
        )

    def notify_task_overdue(self, user, task):
        self.email_client.send(
            user.email,
            f"Task atrasada: {task.title}",
            f"Olá {user.name},\n\nA task '{task.title}' está atrasada!\n\n"
            f"Data limite: {task.due_date}",
        )
