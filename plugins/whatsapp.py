from plugins import Plugin
from plugins.contacts import find_contact


class SendWhatsApp(Plugin):
    name = 'send_whatsapp'
    description = 'Send a WhatsApp message to a saved contact.'
    parameters = {'contact': 'contact name', 'message': 'message text'}
    required = ('contact', 'message')
    confirm = True

    def summary(self, arguments):
        return f"send \"{arguments.get('message', '')}\" to {arguments.get('contact', '')} on WhatsApp"

    def run(self, contact, message):
        person = find_contact(contact, 'phone')
        import pywhatkit  # checks for internet at import time
        pywhatkit.sendwhatmsg_instantly(person['phone'].replace(' ', ''), message, wait_time=15, tab_close=True)
        return f"sent to {person['name']}: {message}"
