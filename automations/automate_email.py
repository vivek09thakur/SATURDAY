import json
import pywhatkit as pw
import speech_recognition as sr

data_file = './database/email_database.json'

    
def extract_contact_name(user_input):
    junk_words = ['send','saturday','an','a','email','mail','emails','mails','gmail','to',
                 'can','you','now','another','please','just','now','hey','email','mail']
    words = user_input.lower().split()
    for word in junk_words:
        words.remove(word) if word in words else None
    contact_name = ''.join(words)
    print(contact_name)
    return contact_name

def listen_for_mail(recognizer):
    voice_input = ''
    try:
        with sr.Microphone() as source:
            print('Listening for mail...')
            audio = recognizer.listen(source=source,timeout=30,phrase_time_limit=5)
        voice_input = recognizer.recognize_google(audio)
        print('\nMessage  : {}'.format(voice_input))
    except sr.UnknownValueError:
        pass
    except sr.RequestError:
        print('Network error.')
    except sr.WaitTimeoutError:
        pass
    except TimeoutError:
        pass
    except Exception as e :
        pass
    return voice_input.lower()


def mail_sender(user_input):
    try:
        contact_name = extract_contact_name(user_input)
        mail_address = None
        with open(data_file ,'r') as file:
            email_data = json.load(file)
        for contact in email_data['contacts']:
            if contact['name'].lower() == contact_name.lower():
                mail_address = contact['email_id']
                break
        recognizer = sr.Recognizer()
        print('Listening for mail subject....')
        mail_body = listen_for_mail(recognizer)
        print('Listening for mail body....')
        mail_subject = listen_for_mail(recognizer)
        pw.send_mail('your_email@example.com','YOUR_EMAIL_PASSWORD',mail_subject,mail_body,mail_address)     
    except Exception as e:
        print(e)
        print('Contact not found')
    