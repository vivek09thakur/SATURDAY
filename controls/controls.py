import webbrowser
import requests
import csv

class CONTROLS:
    
    def __init__(self,web_data_file,contacts_file):
        self.web_data_file = web_data_file
        self.contacts_file = contacts_file
        self.commands = [
            
        ]
        
    def read_csv(self,file_name):
        try:
            with open(file_name) as f:
                readed_data = csv.reader(f,delimiter=',')
        except Exception as e:
            print(f'Error while reading {file_name} , error occured : {e}')
        return readed_data
    

    def web_surfing(self,user_input):
        web_data = self.read_csv(self.web_data_file)
        site_names = web_data['site_name']
        for sites in site_names:
            if sites in user_input:
                try:
                    webbrowser.open_new_tab(sites['web_address'])
                except Exception as e:
                    print(f'ERROR {e} Occured during web surfing')
    
    # def send_message(self,message):
        
                    
    def connect_people(self,user_input):
        contacts = self.read_csv(self.contacts_file)
        connections = contacts['contact_names']
        for connection in connections:
            if user_input in connection:
                print(f'contact found for : {connections[connection]}')
        