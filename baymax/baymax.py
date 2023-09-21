import random
import datetime
import numpy as np
import tensorflow as tf
import speech_recognition as sr
import pyttsx3
import os.path
import json
import time

from .support import Utils
from .automation_controls import AUTOMATION_CONTROLS


class BAYMAX:
    
    def __init__(self,intents_file_path,model_path,open_weather_api,contacts_file,web_data,
                 accuracy_stats=False):
        # INITIALIZING PARAMETERS
        self.intents_file_path = intents_file_path
        self.model_path = model_path
        self.open_weather_api = open_weather_api
        self.contact_file = contacts_file
        self.webdata_file = web_data
        self.accuracy_stats = accuracy_stats
        # INITIALIZING VARIABLES
        self.words = []
        self.classes = []
        self.documents = []
        self.training_data = []
        self.model = None
        # INITIALIZING OBJECTS
        self.utils = Utils(self.open_weather_api)
        self.automation_controls = AUTOMATION_CONTROLS(self.contact_file,self.webdata_file)
        # INITIALIZING INTENTS DATA
        with open(self.intents_file_path) as f: 
            self.intents = json.load(f)
        # INITIALIZING SPEECH ENGINE
        self.engine = pyttsx3.init()
        # TASK CATEGORIES
        self.task_catogeries = {
            ('search','about','google','about'):self.automation_controls.search_web,
            ('search','location','where','is','location','of'):self.automation_controls.search_location,
            ('play','video','song','music'):self.automation_controls.play_video,
            ('open','surf','website','site','check','have i got any'):self.automation_controls.surf_web,
        }
        pass
    
    def load_data(self):
        for intent in self.intents['intents']:
            for pattern in intent['patterns']:
                words_in_pattern = pattern.lower().split()
                self.words.extend(words_in_pattern)
                self.documents.append((words_in_pattern,intent['id']))
                if intent['id'] not in self.classes:
                    self.classes.append(intent['id'])
        self.words = sorted(list(set(self.words)))
        self.classes = sorted(list(set(self.classes)))
        
    def process_data(self):
        for doc in self.documents:
            bag = [1 if word in doc[0] else 0 for word in self.words]
            output_row = [0]*len(self.classes)
            output_row[self.classes.index(doc[1])] = 1
            self.training_data.append([bag,output_row])
            
        random.shuffle(self.training_data)
        
    def build_model(self):
        self.model = tf.keras.Sequential([
            
                    tf.keras.layers.Dense(512,input_shape=(len(self.words),),activation='relu'), # 1st layer
                    tf.keras.layers.Dropout(0.5),

                    tf.keras.layers.Dense(256,activation='relu'), # 2nd layer
                    tf.keras.layers.Dropout(0.25),

                    tf.keras.layers.Dense(128,activation='relu'), # 3rd layer
                    tf.keras.layers.Dropout(0.12),

                    tf.keras.layers.Dense(64,activation='relu'), # 4th layer
                    tf.keras.layers.Dropout(0.06),
            
                    tf.keras.layers.Dense(32,activation='relu'), # 5th layer
                    tf.keras.layers.Dropout(0.03),
                    
                    tf.keras.layers.Dense(16,activation='relu'), # 6th layer
            
                    tf.keras.layers.Dense(len(self.classes), activation='softmax')
        ])
        
        self.model.compile(optimizer='adam',
                      loss='categorical_crossentropy',
                      metrics=['accuracy'])
        
    def train_model(self):
        train_x = np.array([data[0] for data in self.training_data])
        train_y = np.array([data[1] for data in self.training_data])
        self.model.fit(train_x,train_y,epochs=6000,batch_size=300,verbose=2)
        self.model.save(self.model_path)
        
        
    def create_model(self):
        if os.path.isfile(self.model_path):
            self.model = tf.keras.models.load_model(self.model_path)
        else:
            self.build_model()
            self.train_model()
            
    def generate_response(self,user_input):
        
        input_words = user_input.lower().split()
        input_bag = [0]*len(self.words)
        for w in input_words:
            if w in self.words:
                input_bag[self.words.index(w)] = 1
            
        results = self.model.predict(np.array([input_bag]),verbose=0)
        most_probable_class_index = np.argmax(results[0])
        tag = self.classes[most_probable_class_index]
        confidence = results[0][most_probable_class_index]
        
        if self.accuracy_stats == True:
            print(f'accuracy -- {confidence}')
            
        responses = []
        
        for intent in self.intents['intents']:
            if intent['id'] == tag:
                responses = intent['response']
                
        if tag == 'weather':
            # fetch weather
            current_weather = self.utils.fetch_weather(user_input)
            replaced_responses = [
                response.replace("[weather_info]",current_weather)
                for response in responses]
            return random.choice(replaced_responses)
        
        if tag == 'time':
            # returns the current time as response
            current_time = datetime.datetime.now().strftime("%H:%M")
            replaced_responses = [
                response.replace("[current time]",current_time)
                for response in responses]
            return random.choice(replaced_responses)
        
        if tag=='date':
            # returns the current date as response
            current_date = datetime.datetime.now().strftime("%m-%d-%Y")
            replaced_responses = [
                response.replace("[today_date]",current_date)
                for response in responses]
            return random.choice(replaced_responses)
        
        if tag=='wikis':
            # returns information by fetching wikipedia
            fetched_info = self.utils.get_wiki_data(user_input)
            replaced_responses = [
                response.replace("[result_from_wikis]",fetched_info)
                for response in responses]
            return random.choice(replaced_responses)
                    
        return random.choice(responses)
    
    def get_input(self,recognizer):
        voice_input = None
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
        try:
            voice_input = recognizer.recognize_google(audio)
            voice_input = str(voice_input)
            print(f'=> {voice_input}')
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
        
    def type_response(self,text):
        print('=> ',end='')
        for char in text:
            print(char,end='',flush=True)
            time.sleep(0.0005)
        print('\n')
            
    def execute_command(self,user_input,debug_mode=False):
        user_input = user_input.lower()
        input_words = user_input.split()
        try:
            for task in self.task_catogeries.keys():
                if any(word in input_words for word in task):
                    self.task_catogeries[task](user_input)
                    break
                else:
                    pass
        except Exception as e:
            pass
            if debug_mode == True:
                print('ERROR OCCURED => {}'.format(e))
                
    def introduce(self):   
        def wish_me_my_birthday(self):
            my_bithday = datetime.datetime.strptime('06-05','%d-%m').date()
            if datetime.datetime.now().month == my_bithday.month and datetime.datetime.now().day == my_bithday.day:
                self.speak('Happy Birthday sir.')
                
        current_time = datetime.datetime.now().strftime("%H:%M")       
        if int(current_time.split(':')[0]) < 12:
            self.speak(f'Good Morning sir. How can I help you today?')
        elif int(current_time.split(':')[0]) < 16:
            self.speak(f'Good Afternoon sir. How can I help you today?')
        elif int(current_time.split(':')[0]) < 20:
            self.speak(f'Good Evening sir. How can I help you today?')
            
        wish_me_my_birthday(self)