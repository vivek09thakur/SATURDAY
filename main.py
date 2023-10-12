from baymax.baymax import BAYMAX

params = [
    'dataset/intent/intents.json', # intents.json path
    'baymax/baymax.h5', # model path
    '81204e86088679091c3fda217e34a1ca', # open weather api key
]

baymax = BAYMAX(params[0],params[1],params[2],accuracy_stats=True)
train_X,train_Y = baymax.process_training_data()

if __name__=='__main__':
    
    baymax.train_model(train_X,train_Y)
    baymax.introduce()
      
    while True:
        user_input = input('=> ')
        if user_input:
            response = baymax.generate_response(user_input)
            baymax.type_response(response)
            baymax.speak(response)