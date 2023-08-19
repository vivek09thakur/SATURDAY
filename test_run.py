from baymax.baymax import BAYMAX
import speech_recognition as sr

intents = './dataset/intent/intents.json'
model = './baymax/baymax.h5'
open_weather_api = '81204e86088679091c3fda217e34a1ca'
accuracy_stats = True

baymax = BAYMAX(intents,model,open_weather_api,accuracy_stats)

if __name__ =='__main__':
    
    baymax.load_data()
    baymax.process_data()
    baymax.create_model()
    recog = sr.Recognizer()
    
    while True:
        # main-loop
        user_input = baymax.get_input(recog)
        response = baymax.generate_response(user_input)
        print(f'=> {response}')
        baymax.speak(response)