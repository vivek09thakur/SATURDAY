import pywhatkit as pw
import json

data_file = "./database/contact_database.json"

with open(data_file, "r") as file:
    data = json.load(file)
    
def extract_contact_name(user_input):
    common_words = ['send','a','message','to','say','send','tell','him','hey','hello','just'
                    'her','that','that','saturday','Saturday','another','whatsapp','another']
    words = user_input.lower().split()
    for word in common_words:
        words.remove(word) if word in words else None
    contact_name = ' '.join(words)
    return contact_name


def message_sender(user_input,message):
    try:
        recipient_name = extract_contact_name(user_input)
        phone_number = None
        for contact in data["contacts"]:
            if contact["name"].lower() == recipient_name.lower():
                phone_number = contact["phone_number"]
                break
        pw.sendwhatmsg_instantly(phone_number, message)
        # pag.click('enter')
        # If phone number not found, exit the program
        if phone_number is None:
            print(f"Phone number not found for {recipient_name}")
            exit()
    except Exception as e:
        print('Contact not found')
