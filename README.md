## TODO IN THIS PROJECT

### NOT COMPLETEDS

- [ ] Add a Machine Learning based `execute_command` function that can handle more complex commands and classify them into the correct category using intent returned by the `generate_response` function.
> Intents for tasks starts from intent id 38
- [ ] Handle the case where the user has no internet connection
- [ ] Add a way to change the default location

### COMPLETED

- [x] A Neural Network Model having accuracy of 99.9% for classifying user's intent and generating a response accordingly.
- [x] A advanced `generate_response` function that takes in a user's input and returns a response based on the intent of the user's input and the current state of the conversation. And able to handle dynamic responses. such as `current_time` and `current_date` etc.
- [x] Impelemented speak functionalty using `pyttsx3` library and speech recognition using `speech_recognition` library to make this model a voice assistant.
- [x] Implemented a `typed_response` function that will simulate typing effect on the screen.
