from baymax.baymax import baymax

Baymax = baymax(
        intent_file = './dataset/intent/intents.json',
        model_name = './baymax/baymax.h5',
        open_weather_api = '81204e86088679091c3fda217e34a1ca',
        accuracy_stats = True
    )

Baymax.load_data()
Baymax.process_data()
Baymax.create_model()

if __name__ =='__main__':
    while True:
        user_input = input('=> ')
        response = Baymax.generate_response(user_input)
        print(f'=> {response}')