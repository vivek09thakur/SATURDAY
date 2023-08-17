from baymax.baymax import BAYMAX

intents = './dataset/intent/intents.json'
model = './baymax/baymax.h5'
open_weather_api = '81204e86088679091c3fda217e34a1ca'
accuracy_stats = True

baymax = BAYMAX(intents,model,open_weather_api,accuracy_stats)

baymax.load_data()
baymax.process_data()
baymax.create_model()

if __name__ =='__main__':
    while True:
        user_input = input('=> ')
        response = baymax.generate_response(user_input)
        print(f'=> {response}')