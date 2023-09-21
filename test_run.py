from baymax.baymax import BAYMAX

params = [
    './dataset/intent/intents.json', # intents.json path
    './baymax/baymax.h5', # model path
    '81204e86088679091c3fda217e34a1ca', # open weather api key
    './dataset/user/contacts.csv', # contacts data
    './dataset/user/web_data.csv' # web data
]

baymax = BAYMAX(params[0],params[1],params[2],params[3],params[4],accuracy_stats=True)
baymax.introduce()

if __name__=='__main__':
    
    baymax.load_data()
    baymax.process_data()
    baymax.create_model()    
    
    while True:
        user_input = input('=> ')
        if user_input:
            response = baymax.generate_response(user_input)
            baymax.type_response(response)
            baymax.speak(response)
        # TODO : # to add a method that will classify the task and execute it using ML techniques
        #    baymax.execute_command(user_input,intents,classify_task=True) # <= Something like this