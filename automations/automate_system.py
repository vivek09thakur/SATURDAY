import pyautogui as pag
import time

def shutdown():
    time.sleep(2)
    pag.hotkey('win')
    time.sleep(2)
    pag.click(1262,965)
    time.sleep(2)
    pag.click(1282,873)
    
def open_search():
    pag.click(825,1048)

def open_feed():
    pag.click(879,1050)
    
def close_feed():
    pag.click(879,1050)
