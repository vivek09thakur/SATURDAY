from baymax.baymax import BAYMAX
from controls.controls import AUTOMATION_CONTROLS

params = [
    './dataset/intent/intents.json',
    './baymax/baymax.h5',
    '81204e86088679091c3fda217e34a1ca',
    './dataset/user/contacts.csv',
    './dataset/user/web_data.csv'
]

baymax = BAYMAX(params[0],params[1],params[2],accuracy_stats=True)
baymax_automate = AUTOMATION_CONTROLS(params[3],params[4])

if __name__=='__main__':
    
    baymax.load_data()
    baymax.process_data()
    baymax.create_model()    
    
    while True:
        user_input = input('=> ')
        response = baymax.generate_response(user_input)
        print(f'=> {response}')
        baymax.speak(response)