# Fixed values shared across Saturday. Tunable knobs live in common.common.Config instead.

# --- identity -------------------------------------------------------------------------------------
NAME = 'Saturday'
AUTHOR = 'Vivek Thakur'
PERSONA = (
    f'You are {NAME}, a personal voice assistant created by {AUTHOR}. '
    "You call the user 'boss'. You are warm, casual and a bit playful, like a close friend. "
    'Your replies are spoken aloud, so answer in one or two short plain sentences: no markdown, no lists, no emojis. '
    'Remember what the user tells you, such as their name and how their day went.'
)
TOOL_PROMPT = (
    'You can use tools. When the user asks for something that needs one, reply with only:\n'
    '<tool_call>{"name": "tool_name", "arguments": {"param": "value"}}</tool_call>\n'
    'Tools:\n{tools}\n'
    'This computer runs {platform}. '
    'The result arrives in a tool message; then answer using only that result. '
    'Do not use tools for normal conversation.'
)

# --- model ----------------------------------------------------------------------------------------
BASE_MODEL = 'HuggingFaceTB/SmolLM2-1.7B-Instruct'  # SmolLM2-360M-Instruct is faster on CPU but worse at tool calls
OUT_DIR = 'out-saturday'  # fine-tuned model (HF format)
SEED = 1337
IGNORE_INDEX = -100

# --- data -----------------------------------------------------------------------------------------
DATA_DIR = 'data'
CONVERSATIONS_PATH = f'{DATA_DIR}/conversations.txt'
CONTACTS_PATH = f'{DATA_DIR}/contacts.json'
SPEAKERS = {'User': 'user', NAME: 'assistant', 'Tool': 'tool'}
SEPARATOR = '---'
ENV_FILE = '.env'

# --- voice ----------------------------------------------------------------------------------------
WHISPER_MODEL = 'base.en'  # tiny.en / base.en / small.en / medium.en
TTS_VOICE = 'en-IN-PrabhatNeural'
SAMPLE_RATE = 16000

# --- conversation ---------------------------------------------------------------------------------
GOODBYE_WORDS = ('bye', 'goodbye', 'good night', 'see you later')
YES_WORDS = ('yes', 'yeah', 'yep', 'yup', 'sure', 'ok', 'okay', 'go ahead', 'do it', 'allow')
GREETINGS = {(0, 12): 'a warm good morning boss', (12, 18): 'good afternoon boss', (18, 24): 'good evening boss'}

# --- plugins --------------------------------------------------------------------------------------
SITES = {
    'gmail': 'https://mail.google.com/mail/u/0/#inbox',
    'maps': 'https://www.google.com/maps',
    'github': 'https://github.com',
    'stackoverflow': 'https://stackoverflow.com',
    'instagram': 'https://www.instagram.com',
    'facebook': 'https://www.facebook.com',
    'linkedin': 'https://www.linkedin.com',
    'twitter': 'https://x.com',
    'x': 'https://x.com',
    'whatsapp': 'https://web.whatsapp.com',
    'snapchat': 'https://web.snapchat.com',
    'pinterest': 'https://in.pinterest.com',
    'youtube': 'https://www.youtube.com',
}
WEATHER_URL = 'https://api.openweathermap.org/data/2.5/weather'
YOUTUBE_SEARCH_URL = 'https://www.youtube.com/results?search_query={query}'
YOUTUBE_VIDEO_URL = 'https://www.youtube.com/watch?v={video_id}'
GOOGLE_SEARCH_URL = 'https://www.google.com/search?q={query}'
GOOGLE_MAPS_URL = 'https://www.google.com/maps/search/{query}'
USER_AGENT = f'Mozilla/5.0 {NAME}/2.0'
HTTP_TIMEOUT = 10
