import pyttsx3
import datetime
import speech_recognition as sr
import speedtest
import requests
import time



weather_api_key = "YOUR_OPENWEATHER_API_KEY"

def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate',180)
    engine.setProperty('volume',1.0)
    engine.say(text)
    engine.runAndWait()

def listen_for_input(recognizer,microphone):
    voice_input = ''
    try:
        with microphone as source:
            print('Listening...\n')
            audio = recognizer.listen(source=source, timeout=5, phrase_time_limit=5)
        voice_input = recognizer.recognize_google(audio)
        print('user said : {}'.format(voice_input))
    except sr.UnknownValueError:
        pass
    except sr.RequestError:
        print('Network error.')
    except sr.WaitTimeoutError:
        pass
    except TimeoutError:
        pass

    return voice_input.lower()

        
def check_internet_speed():
    print('\n\nChecking Network Connection...')
    st = speedtest.Speedtest()
    download_speed = st.download(threads=1)
    net_speed = download_speed/1000000
    return net_speed
    
    
def extract_city_name(user_input):
    common_words = ['what', 'is', 'of', 'outside', 'today', 'how', '\'','s' , 'search','how\'s',
                    'where','is','saturday','do','you','know','have','ever','visited','weather','the','visited']
    words = user_input.lower().split()
    for word in common_words:
        words.remove(word) if word in words else None
    city_name = ' '.join(words)
    return city_name

# Get Weather Info Function  
def get_weather_info(weather_api_key, city):
    city = extract_city_name(city)
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = base_url + "appid=" + weather_api_key + "&q=" + city
    response = requests.get(complete_url)
    data = response.json()
    if data["cod"] != "404":
        weather_info = {
            "temperature": round(data["main"]["temp"] - 273.15, 2), # Temperature in Celsius
            "humidity": data["main"]["humidity"], # Humidity percentage
            "wind_speed": data["wind"]["speed"], # Wind speed in m/s
            "description": data["weather"][0]["description"], # Short weather description
        }
        return weather_info
    else:
        return None
    
def do_weather_forecast(user_input):
    if ('weather' in user_input) and ('of' in user_input):
        weather_info = get_weather_info(weather_api_key,user_input)
        if weather_info:  
            speak('Boss ')  
            speak(f"Temperature: {weather_info['temperature']}°C"+f"Humidity: {weather_info['humidity']}%"+f"Wind Speed: {weather_info['wind_speed']} m/s")
            speak(f"{weather_info['description']}")
            print(f"Temperature: {weather_info['temperature']}°C")
            print(f"Humidity: {weather_info['humidity']}%")
            print(f"Wind Speed: {weather_info['wind_speed']} m/s")
            print(f"Description: {weather_info['description']}")
        else:
            print("City not found.") 
        return True  
# wish me 
def wish_me():
    WIDTH = 20
    for i in range(WIDTH + 6):
        arrow = "[" + "#" * i + "]"
        print(f'[nltk data] : Training AI.yml {arrow}')
        time.sleep(0.003)
        hour = int(datetime.datetime.now().hour)
    if hour >= 0 and hour < 12:
        speak("a warm good morning boss")
        weather_info = get_weather_info(weather_api_key,'Ranchi')
        speak('boss, here i have today\'s weathers report')
        speak(f"Temperature: {weather_info['temperature']}°C"+f"Humidity: {weather_info['humidity']}%"+f"Wind Speed: {weather_info['wind_speed']} meters per seconds")
    elif hour >= 12 and hour < 18:
        speak("good afternoon boss")
        weather_info = get_weather_info(weather_api_key,'Ranchi')
        speak('boss, here i have today\'s afternoon weathers report ')
        speak(f"Temperature: {weather_info['temperature']}°C"+f"Humidity: {weather_info['humidity']}%"+f"Wind Speed: {weather_info['wind_speed']} meters per seconds")
    else:
        speak("good Evening boss")
        