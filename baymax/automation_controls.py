from .support import text_processing, web_support


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
        
        self.contact_names,self.contact_numbers = self.text_processor.read_csv_file(
            self.contact_file,
            self.contact_names,
            self.contact_numbers
        )
        self.site_names,self.site_urls = self.text_processor.read_csv_file(
            self.webdata_file,
            self.site_names,
            self.site_urls
        )
    
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
        seached_site = self.text_processor.search_site_names(user_input)
        try:
            index = self.site_names.index(seached_site)
            self.web.open_url(self.site_urls[index]) # for debugging
        except Exception as e:
            print('ERROR OCCURED => {}'.format(e))
            
        
            
# Test code
# if __name__ == '__main__':
#     test_parameters = ['./dataset/user/contacts.csv','./dataset/user/web_data.csv']
#     test_control = AUTOMATION_CONTROLS(test_parameters[0],test_parameters[1])
#     test_control.surf_web('hey baymax open google')
    # test_control.search_web('baymax search about apples')
    # test_control.play_video('baymax play chammak challo')
    # test_control.search_location('baymax where is india')
    # test_control.send_message('mom')
    # print(test_control.search_contact_names('baymax search about mom'))
    # test_control.execute_command('baymax search about quantum physics in physics')