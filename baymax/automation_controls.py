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
        
    def open_site(self,site_url):
        try:
            webbrowser.open(site_url)
        except:
            print('Error opening site')
    
    def surf_web(self,user_input):
        if user_input in self.site_names:
            site_index = self.site_names.index(user_input)
            self.open_site(self.site_urls[site_index])
        else:
            print('Site not found')
            
            
# Test code
# if __name__ == '__main__':
#     test_parameters = ['./dataset/user/contacts.csv','./dataset/user/web_data.csv']
#     test_control = AUTOMATION_CONTROLS(test_parameters[0],test_parameters[1])
#     test_control.surf_web('google')
