import random
import datetime
import numpy as np
import tensorflow as tf
from .support import Utils
import os.path
import json

class baymax:
    
    def __init__(self,intents_file_path,model_path,open_weather_api,accuracy_stats=False):
        self.intents_file_path = intents_file_path
        self.model_path = model_path
        self.open_weather_api = open_weather_api
        self.words = []
        self.classes = []
        self.documents = []
        self.training_data = []
        self.model = None
        self.utils = Utils(self.open_weather_api)
        self.accuracy_stats = accuracy_stats
        pass
    
    def load_intents(self):
        with open(self.intents_file_path) as f: 
            intents = json.load(f)
        for intent in intents['intents']:
            for pattern in intent['patterns']:
                words_in_pattern = pattern.lower().split()
                self.words.extend(words_in_pattern)
                self.documents.append((words_in_pattern,intent['id']))
                if intent['id'] not in self.classes:
                    self.classes.append(intent['id'])
        self.words = sorted(list(set(self.words)))
        self.classes = sorted(list(set(self.classes)))
        
    def preprocess_data(self):
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
        
        
    def load_or_build_model(self):
        if os.path.isfile(self.model_path):
            self.model = tf.keras.models.load_model(self.model_path)
        else:
            self.build_model()
            self.train_model()
            
    def generate_response(self,user_input):
        
        input_words = user_input.lower().split()
        input_bag = [0]*len(self.words)
        for w in input_words:
            input_bag[self.words.index(w)] = 1
            
        results = self.model.predict(np.array([input_bag]))[0]
        most_probable_class_index = np.argmax(results)
        tag = self.classes[most_probable_class_index]
        confidence = results[0][most_probable_class_index]
        
        if self.accuracy_stats == True:
            print(f'accuracy -- {confidence}')
            
        responses = []
        
        for intent in self.intents['intents']:
            if intent['id'] == tag:
                responses = intent['responses']
                
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