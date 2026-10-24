from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer

with open('./neural_cortex/training_data.txt','r') as f :
    training_data = f.readlines()
    
chatbot = ChatBot('SATURDAY',
            logic_adapters=[
                'chatterbot.logic.BestMatch',
                'chatterbot.logic.TimeLogicAdapter',
            ],
            storage_adapter='chatterbot.storage.SQLStorageAdapter',
            database_uri='sqlite:///./database/database.db',
        )
trainer = ChatterBotCorpusTrainer(chatbot)
trainer.train(
    'chatterbot.corpus.english',
    'chatterbot.corpus.english.conversations')

def generate_response(user_input):
    response = chatbot.get_response(user_input)
    return response