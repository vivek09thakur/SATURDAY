import csv
import webbrowser
import requests
import wikipedia


class Utils:

    def __init__(self, api_key):
        self.api_key = api_key
        self.junk_words = ['max', 'search', 'about', 'wikipedia', 
                           'play', 'google','explain', 'define', 
                           'describe', 'get info about']

    def fetch_weather(self, city):

        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}"
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:

            weather = data.get('weather', [{}])[0]
            
            description = weather.get('description', '')
            temp = data.get('main', {}).get('temp', '')
            humidity = data.get('main', {}).get('humidity', '')

            return f'''
                    Weather of {city} is quite {description}, 
                    with temperature around {temp} kelvins,
                    and humidity above {humidity} RH.
                '''  
        else:
            return f"Sorry, failed to get the weather report for {city}."

    def get_query(self, user_input):

        cleaned_up_query = [word for word in user_input.split() 
                            if word.lower() not in self.junk_words]      
        return ' '.join(cleaned_up_query)

    def get_wiki_data(self, user_input):

        query = self.get_query(user_input)
        try:
            wiki_result = wikipedia.summary(query, sentences=3)
            return wiki_result
        except Exception:
            return "Sorry, I couldn't find any information about it."
        

class text_processing:
    
    def __init__(self,site_names,contact_names):
        self.site_names = site_names
        self.contact_names = contact_names
        self.junk_words = [
            'baymax','search','about','google','play','youtube',
            'open','website','site','surf','browse','internet',
            'wikipedia','where','is','location of'
        ]
        
    def clear_query(self,user_input):
        for word in self.junk_words:
            user_input = user_input.replace(word,'')
        return user_input.strip()
    
    def search_contact_names(self,user_input):
        for name in self.contact_names:
            if name in user_input:
                return name
    
    def search_site_names(self,user_input):
        for name in self.site_names:
            if name in user_input:
                return name
            
    def read_csv_file(self,csv_file,list_1,list_2):
        with open(csv_file,'r') as f:
            reader = csv.reader(f)
            for row in reader:
                list_1.append(row[0])
                list_2.append(row[1])
            return list_1,list_2
        
        
class web_support:
    
    def open_url(self,url):
        try:
            webbrowser.open(url)
        except Exception as e:
            print('Sorry, I could not open the url. Please try again. {}'.format(e))
    
    def play_video(self,query):
        try:
            url = 'https://www.youtube.com/results?search_query={}'.format(query)
            self.open_url(url)
        except Exception as e:
            print('Sorry, I could not play the video. Please try again. {}'.format(exit))
            
    def search_web(self,query):
        try:
            url = 'https://www.google.com/search?q={}'.format(query)
            self.open_url(url)
        except Exception as e:
            print('Sorry, I could not search the web. Please try again. {}'.format(e))
        
    def search_location(self,query):
        try:
            url = 'https://www.google.com/maps/place/{}'.format(query)
            self.open_url(url)
        except Exception as e:
            print('Sorry, I could not search the location. Please try again. {}'.format(e))