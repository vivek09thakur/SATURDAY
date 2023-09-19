import csv
from support import web_support
from support import text_processing

class AUTOMATION_CONTROLS:
    
    def __init__(self,contact_file,webdata_file):
        self.contact_file = contact_file
        self.webdata_file = webdata_file
        self.contact_names = []
        self.contact_numbers = []
        self.site_names = []
        self.site_urls = []
        self.web = web_support()
        self.text_processor = text_processing(self.site_names,self.contact_names)
        
        with open(self.contact_file,'r') as f:
            reader = csv.reader(f)
            for row in reader:
                self.contact_names.append(row[0])
                self.contact_numbers.append(row[1])
        
        with open(self.webdata_file,'r') as f:
            reader = csv.reader(f)
            for row in reader:
                self.site_names.append(row[0])
                self.site_urls.append(row[1])
    
    def search_web(self,user_input):
        query = self.text_processor.clear_query(user_input)
        self.web.search_web(query)
    
    def search_location(self,user_input):
        query = self.text_processor.clear_query(user_input)
        self.web.search_location(query)
        
    def play_video(self,user_input):
        query = self.text_processor.clear_query(user_input)
        self.web.play_video(query)
        
    def surf_web(self,user_input):
        if user_input in self.site_names:
            site_index = self.site_names.index(user_input)
            self.web.open_url(self.site_urls[site_index])
        else:
            print('Site not found')
            

            
# Test code
if __name__ == '__main__':
    test_parameters = ['./dataset/user/contacts.csv','./dataset/user/web_data.csv']
    test_control = AUTOMATION_CONTROLS(test_parameters[0],test_parameters[1])
    test_control.surf_web('hey baymax open google')
    test_control.search_web('baymax search about apples')
    test_control.play_video('baymax play chammak challo')
    test_control.search_location('baymax where is india')
    # test_control.send_message('mom')
    # print(test_control.search_contact_names('baymax search about mom'))