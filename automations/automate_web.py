import webbrowser
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyautogui as pag



# Opens Random Sites
def open_site(url):
    try:
        webbrowser.open_new_tab(url)
    except Exception as e :
        print(e)
        print('Network Error')       
# Closes Chrome Tab using Ctrl+W  
def close_tab():
    pag.hotkey('ctrl','w')
    
# For Getting the name of content to search or play
def extract_query(user_input):
    common_words = ['search','about','play','video','wikipedia','google','saturday']
    words = user_input.lower().split()
    for word in common_words:
        words.remove(word) if word in words else None
    query = ' '.join(words)
    return query  

driver_path ='C:/Users/Lenovo V15/.cache/selenium/chromedriver/win32/113.0.5672.63/chromedriver.exe'
brave_browser = 'C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe'

# Plays Videos and Song on youtube  
def play_on_youtube(video_name):
    try:
        video = extract_query(video_name)
        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = brave_browser
        chrome_options.add_experimental_option('detach',True)
        driver = webdriver.Edge(options=chrome_options,executable_path=driver_path)
        wait = WebDriverWait(driver, 10)
        visible = EC.visibility_of_element_located
        driver.get('https://www.youtube.com/results?search_query={}'.format(str(video)))
        wait.until(visible((By.ID, "video-title")))
        driver.find_element(By.ID,"video-title").click()
    except Exception as e :
        print(e)
        print('Network error , Boss!')          
# Searches the query   
def search_web(query):
    try:
        query = extract_query(query)
        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = brave_browser
        chrome_options.add_experimental_option("detach", True)
        driver = webdriver.Chrome(options=chrome_options,executable_path=driver_path)
        driver.get("https://www.google.com/")
        search_box = driver.find_element(By.NAME,"q")
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        driver.implicitly_wait(5)
        print(driver.title)
    except Exception as e:
        print(e)  
        print('Network Error')     
  
# For Getting the name of location
def extract_city_name(user_input):
    common_words = ['what', 'is', 'of', 'outside', 'today', 'how', '\'','s' , 'search','how\'s',
                    'where','is','saturday','do','you','know','have','ever','visited','weather','the','visited']
    words = user_input.lower().split()
    for word in common_words:
        words.remove(word) if word in words else None
    city_name = ' '.join(words)
    return city_name        

# Get the Info of location
def search_location(place):
    try:
        place = extract_city_name(place)
        place_url = 'https://www.google.com/maps/search/'+place
        webbrowser.open_new_tab(place_url)
    except Exception as e :
        print(e)
        print('Network error , Boss! ..')
        