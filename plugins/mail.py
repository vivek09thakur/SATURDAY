import os
import smtplib
from email.message import EmailMessage

from common.utils import require_env
from plugins import Plugin
from plugins.contacts import find_contact


class SendEmail(Plugin):
    name = 'send_email'
    description = 'Send an email to a saved contact.'
    parameters = {'contact': 'contact name', 'subject': 'subject line', 'body': 'email text'}
    required = ('contact', 'body')
    confirm = True

    def summary(self, arguments):
        return f"email {arguments.get('contact', '')} about \"{arguments.get('subject') or arguments.get('body', '')[:40]}\""

    def run(self, contact, body, subject='Message from Saturday'):
        person = find_contact(contact, 'email')
        sender, password = require_env('SMTP_EMAIL'), require_env('SMTP_PASSWORD')
        host, port = os.environ.get('SMTP_HOST', 'smtp.gmail.com'), int(os.environ.get('SMTP_PORT', '587'))
        mail = EmailMessage()
        mail['From'], mail['To'], mail['Subject'] = sender, person['email'], subject
        mail.set_content(body)
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(sender, password)
            smtp.send_message(mail)
        return f"emailed {person['name']} ({person['email']}): {subject}"
