import json
import numpy as np
import tensorflow as tf
import random 
import os.path


with open('./intents/intents.json') as f: 
    intents = json.load(f)  # loads intents

# golabal variable
words = []
classes = []
documents = []

# apis and others
open_weather_api = '81204e86088679091c3fda217e34a1ca'


for intent in intents['intents']:
    for pattern in intent['patterns']:
        words_in_pattern = pattern.lower().split()
        words.extend(words_in_pattern)
        documents.append((words_in_pattern,intent['id']))
        if intent['id'] not in classes:
            classes.append(intent['id'])


words = sorted(list(set(words)))
classes = sorted(list(set(classes)))

training_data = []
output = [0]*len(classes)


for doc in documents:
    bag = [] #bags of words
    words_in_pattern = [word.lower() for word in doc[0]]
    for word in words:
        if word in words_in_pattern:
            bag.append(1)
        else:
            bag.append(0)

    output_row = list(output)
    output_row[classes.index(doc[1])] = 1
    training_data.append([bag,output_row])

random.shuffle(training_data)
training_data = np.array(training_data,dtype=object)

# X AND Y
train_x = np.array(training_data[:,0].tolist())
train_y = np.array(training_data[:,1].tolist())

model_path = 'baymax.h5'

if not os.path.isfile(model_path):
    
    # Build the model
    baymax = tf.keras.Sequential([
        
        tf.keras.layers.Dense(512,input_shape=(len(words),),activation='relu'), # 1st layer
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

        tf.keras.layers.Dense(len(classes), activation='softmax')
    ])

    # Compile baymax
    baymax.compile(loss='categorical_crossentropy',optimizer='adam',metrics=['accuracy'])
    # Train baymax
    baymax.fit(train_x,train_y,epochs=6000,batch_size=300,verbose=2)
    # Save baymax
    baymax.save(model_path)

else:
    # Load the model
    baymax = tf.keras.models.load_model(model_path)


def generate_response(user_input):

    input_words = user_input.lower().split()
    input_bag = [0]*len(words)
    for w in input_words:
        if w in words:
            input_bag[words.index(w)] = 1
    results = baymax.predict(np.array([input_bag]),verbose=0)
    most_probable_class_index = np.argmax(results[0])
    tag = classes[most_probable_class_index]
    confidence = results[0][most_probable_class_index]

    responses = []

    for intent in intents['intents']:
        if intent['id'] == tag:
            responses = intent['response']

    return random.choice(responses),confidence

while True:
    user_input = input('=> ')
    response = generate_response(user_input)
    print(f'=> {response[0]}')
    print(f'confidence == {response[1]}')