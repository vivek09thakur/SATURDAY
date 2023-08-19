import speech_recognition as sr
import pyttsx3

class Voice_controls:
    
    def __init__(self):
        self.engine = pyttsx3.init()
        pass
    
    def listen(self,recognizer,microphone):
        voice_input = None
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
            try:
                voice_input = recognizer.recognize_google(audio)
                voice_input = str(voice_input)
            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                print('Network error.')
            except sr.WaitTimeoutError:
                pass
            except Exception as e:
                print(e)
        return voice_input.lower()
        
    def speak(self,text):
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)
        self.engine.say(text)
        self.engine.runAndWait()