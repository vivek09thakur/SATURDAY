import requests
import wikipedia


class Utils:

    def __init__(self, api_key):
        self.api_key = api_key

    def fetch_weather(self, city):
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}"
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            weather = data.get('weather', [{}])[0]
            description = weather.get('description', '')
            temp = data.get('main', {}).get('temp', '')
            humidity = data.get('main', {}).get('humidity', '')

            return f'''Weather of {city} is quite {description}, 
                        with temperature around {temp} kelvins,
                        and humidity above {humidity} RH.'''
        
        else:
            return f"Sorry, failed to get the weather report for {city}."

    def get_query(self, user_input):

        junk_words = ['max', 'search', 'about', 'wikipedia', 'play', 'google',
                      'explain', 'define', 'describe', 'get info about']
        cleaned_up_query = [word for word in user_input.split() if word.lower() not in junk_words]
        return ' '.join(cleaned_up_query)

    def get_wiki_data(self, user_input):
        
        query = self.get_query(user_input)
        try:
            wiki_result = wikipedia.summary(query, sentences=3)
            return wiki_result
        except Exception:
            return "Sorry, I couldn't find any information about it."
