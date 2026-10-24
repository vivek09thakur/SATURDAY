import tensorflow as tf
import numpy as np
import random
import json
import nltk
from nltk.stem.lancaster import LancasterStemmer


with open('./saved_model/intents.json') as file:
    intents = json.load(file)
    
stemmer = LancasterStemmer()
words = []
classes = []
documents = []

for intent in intents['intents']:
    for pattern in intent['patterns']:
        words_in_pattern = nltk.word_tokenize(pattern)
        words.extend(words_in_pattern)
        documents.append((words_in_pattern, intent['tag']))
        if intent['tag'] not in classes:
            classes.append(intent['tag'])
words = [stemmer.stem(word.lower()) for word in words if word != '?']
words = sorted(list(set(words)))
classes = sorted(list(set(classes)))

training_data = []
output = [0] * len(classes)
for doc in documents:
    bag = []
    words_in_pattern = [stemmer.stem(word.lower()) for word in doc[0]]
    for word in words:
        if word in words_in_pattern:
            bag.append(1)
        else:
            bag.append(0)
    output_row = list(output)
    output_row[classes.index(doc[1])] = 1
    training_data.append([bag, output_row])
random.shuffle(training_data)
training_data = np.array(training_data)

model = tf.keras.Sequential([
    tf.keras.layers.Dense(8, input_shape=(len(words),), activation='relu'),
    tf.keras.layers.Dense(8, activation='relu'),
    tf.keras.layers.Dense(len(classes), activation='softmax')
])
model_path = './saved_model/VS2306'
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
model.fit(training_data[:,0].tolist(), training_data[:,1].tolist(), epochs=512, batch_size=8,)
model.save(model_path)


def generate_response(input_text):  
    input_words = nltk.word_tokenize(input_text)
    input_words = [stemmer.stem(word.lower()) for word in input_words]  
    input_bag = [0] * len(words)
    for w in input_words:
        for i, word in enumerate(words):
            if word == w:
                input_bag[i] = 1 
    results = model.predict(np.array([input_bag]))[0] 
    most_probable_class_index = np.argmax(results)
    tag = classes[most_probable_class_index]
    responses = []
    for intent in intents['intents']:
        if intent['tag'] == tag:
            responses = intent['responses']
    return random.choice(responses)