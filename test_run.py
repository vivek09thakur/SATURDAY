from baymax.baymax import BAYMAX
from controls.voice_controls import Voice_controls

intents = './dataset/intent/intents.json'
model = './baymax/baymax.h5'
open_weather_api = '81204e86088679091c3fda217e34a1ca'
accuracy_stats = True

baymax = BAYMAX(intents,model,open_weather_api,accuracy_stats)
controls = Voice_controls()

if __name__ =='__main__':
    
    baymax.load_data()
    baymax.process_data()
    baymax.create_model()
    
    while True:
        # main-loop
        user_input = input('=> ')
        response = baymax.generate_response(user_input)
        print(f'=> {response}')
        controls.speak(response)