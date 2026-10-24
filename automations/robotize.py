import speech_recognition as sr
from automations.utils import (listen_for_input,speak)
from automations.automate_web import (open_site,search_web,play_on_youtube,search_location,close_tab)
from automations.automate_system import (shutdown,open_feed,close_feed)
from automations.automate_whatsapp import (message_sender)
from automations.automate_email import (mail_sender)
from automations.automate_wifi import (check_connected_device)



def web_automation(user_input):  
    if ('search' in user_input and 'about' in user_input):
        search_web(user_input)
        return True
    if ('open' in user_input or 'check' in user_input  or 'got' in user_input or 'have' in user_input) and ('gmail' in user_input or 'emails' in user_input or 'mail box' in user_input): # Gmail 
        open_site('https://mail.google.com/mail/u/0/#inbox')
        return True 
    elif ('play' in user_input) or ('video' in user_input):
       play_on_youtube(user_input)
       return True
    elif ('where' in user_input ) and ('is' in user_input):
        search_location(user_input)
        return True
    elif ('open' in user_input) and ('map' in user_input or 'google maps' in user_input): # Google Maps
        open_site('https://www.google.com/maps')
        return True
    #  Surfing Random sites of daily usage
    elif ('open' in user_input or 'check' in user_input) and ('github' in user_input):   # GitHub
        open_site('https://github.com/vivek09thakur')
        return True
    elif ('open' in user_input or 'check' in user_input) and ('stackoverflow' in user_input): # Stackoverflow
        open_site('stackoverflow.com')
        return True
    elif ('open' in user_input or 'check' in user_input or 'going' in user_input) and 'instagram' in user_input: # Instagram
        open_site('https://www.instagram.com/vivekthakur.exe/')
        return True
    elif ('open' in user_input or 'check' in user_input or 'going' in user_input) and 'facebook' in user_input: # Facebook
        open_site('https://www.facebook.com')
        return True
    elif ('open' in user_input or 'check' in user_input or 'going' in user_input) and 'linkedin' in user_input: # LinkedIn
        open_site('https://www.linkedin.com')
        return True
    elif ('open' in user_input or 'check' in user_input or 'tweets' in user_input) and 'twitter' in user_input: # Twitter
        open_site('https://www.twitter.com')
        return True
    elif ('dm' in user_input or 'have' in user_input or 'open' in user_input) and ('whatsapp' in user_input): # Whatsapp Web
        open_site('https://web.whatsapp.com')
        return True
    elif ('open' in user_input or 'check' in user_input or 'got' in user_input or 'have' in user_input) and ('snaps' in user_input or 'snapchat' in user_input): #Snapchat Web
        open_site('https://web.snapchat.com/vivekthakur.exe')
        return True
    elif ('open' in user_input or 'check' in user_input or 'got' in user_input or 'have' in user_input) and ('pins' in user_input or 'pinterest' in user_input): # pinterest
        open_site('https://in.pinterest.com/')
        return True
    elif ('close' in user_input or 'closed' in user_input or 'exit' in user_input) and ('tab' in user_input or 'chrome tab' in user_input):
        close_tab() 
        return True 
    
def system_automation(user_input):
    if ('shutdown'in user_input or 'turn off' in user_input):
        shutdown()
        return True
    elif ('open' in user_input) and ('feed' in user_input):
        open_feed()
        return True
    elif ('close' in user_input) and ('feed' in user_input):
        close_feed()
        return True
    
def whatsapp_automation(user_input):
    if('send' in user_input) and ('message' in user_input):
        m = sr.Microphone()
        r = sr.Recognizer()
        try:
            print('Say your message')
            message = listen_for_input(r,m)
            message_sender(user_input,message)
            return True
        except Exception as e:
            print(e)
            print('Boss I cannot connect to internet')

def email_automation(user_input):
    if ('send' in user_input) and ('mail' in user_input or 'email' in user_input):
        try:
            mail_sender(user_input)
        except Exception as e:
            print(e)
            print('Boss an unkown network error occured')
            
def get_connected_devices(user_input):
    if ('check' in user_input or 'how many' in user_input ) and 'connected' in user_input:
         devices = check_connected_device()
         for device in devices:
             speak('Okay boss as you say')
             print(f'IP address: {device[0]} MAC address: {device[1]}')