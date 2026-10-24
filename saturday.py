import threading
import speech_recognition as sr
from neural_cortex.generative_model import generate_response
from automations.utils import (listen_for_input,speak,do_weather_forecast,wish_me)
from automations.robotize import (web_automation,whatsapp_automation,system_automation,get_connected_devices)

automations = [web_automation,whatsapp_automation,system_automation,do_weather_forecast,get_connected_devices]
threads = []

def automate(task_func,user_input):
    try:
        if task_func(user_input):
            return True
    except Exception as e :
        print(e)
        pass
    
if __name__ == '__main__':
     wish_me()
     while True:
         microphone = sr.Microphone()
         recognizer = sr.Recognizer()
         user_input = listen_for_input(recognizer,microphone)
         if user_input:      
             response = generate_response(user_input)
             print(f'response : {response}\n')  
             speak(response)
             for automation in automations:
                 t = threading.Thread(target=automate,args=(automation,user_input))
                 threads.append(t)
                 t.start()
             for t in threads:
                 t.join()
             if 'bye' in user_input:
                 break