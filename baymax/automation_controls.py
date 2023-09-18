import webbrowser
import csv

class AUTOMATION_CONTROLS:
    
    def __init__(self,contact_file,webdata_file):
        self.contact_file = contact_file
        self.webdata_file = webdata_file
        self.contact_names = []
        self.contact_numbers = []
        self.site_names = []
        self.site_urls = []
        self.junk_words = [
            'baymax','search','about','google','play','youtube',
            'open','website','site','surf','browse','internet',
            'wikipedia','where','is','location of'
        ]
        
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
        
    def open_site(self,site_url):
        try:
            webbrowser.open(site_url)
        except:
            print('Error opening site')
    
    def search_web(self,user_input):
        query = self.clear_query(user_input)
        self.open_site(f'https://www.google.com/search?q={query}')
    
    def search_location(self,user_input):
        query = self.clear_query(user_input)
        self.open_site(f'https://www.google.com/maps/place/{query}')
        
    def surf_web(self,user_input):
        if user_input in self.site_names:
            site_index = self.site_names.index(user_input)
            self.open_site(self.site_urls[site_index])
        else:
            print('Site not found')
            
    def send_message(self,user_input):
        query = self.clear_query(user_input)
        if query in self.contact_names:
            contact_index = self.contact_names.index(query)
            self.open_site(f'https://web.whatsapp.com/send?phone={self.contact_numbers[contact_index]}')
        else:
            print('Contact not found')

            
# Test code
if __name__ == '__main__':
    test_parameters = ['./dataset/user/contacts.csv','./dataset/user/web_data.csv']
    test_control = AUTOMATION_CONTROLS(test_parameters[0],test_parameters[1])
    # test_control.surf_web('google')
    # print(test_control.clear_query('baymax search about apples'))
    # test_control.search_web('baymax search about apples')
    # test_control.play_video('baymax play chammak challo')
    # test_control.search_location('baymax where is india')
    # test_control.send_message('mom')
    # print(test_control.search_contact_names('baymax search about mom'))s
