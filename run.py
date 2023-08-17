from baymax.baymax import baymax

intent_file = './dataset/intent/intents.json'
model_name = './baymax/baymax.h5'
open_weather_api = '81204e86088679091c3fda217e34a1ca'
accuracy_stats = True

if __name__ =='__main__':
    
    Baymax = baymax(intent_file,model_name,open_weather_api,accuracy_stats)
    Baymax.load_intents()
    Baymax.preprocess_data()
    Baymax.load_or_build_model()
    
    while True:
        user_input = input('=> ')
        response = Baymax.generate_response(user_input)
        print(f'=> {response}')