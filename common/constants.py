# Fixed values shared across Saturday. Tunable knobs live in common.common.Config instead.

# --- identity -------------------------------------------------------------------------------------
NAME = 'Saturday'
AUTHOR = 'Vivek Thakur'
PERSONA = (
    f'You are {NAME}, a personal voice assistant created by {AUTHOR}, your boss. '
    'You are warm, casual and a bit playful, like a close friend. '
    'Your replies are spoken aloud, so answer in one or two short plain sentences: no markdown, no lists, no emojis. '
    'Remember what the user tells you, such as how their day went.'
)
CONTEXT_PROMPT = '{user} It is {time}.'  # appended at inference with the logged-in user and the current time
GUEST_PROMPT = ("They are not your owner: be polite, keep Vivek's personal details private, "
                'and politely refuse anything that changes this computer or sends messages.')
OWNER_TITLE = 'boss'
GUEST_TITLE = 'friend'
USERS_PATH = 'data/users.json'
TOOL_PROMPT = (
    'You can use tools. When the user asks for something that needs one, reply with only:\n'
    '<tool_call>{"name": "tool_name", "arguments": {"param": "value"}}</tool_call>\n'
    'Tools:\n{tools}\n'
    'This computer runs {platform}. '
    'The result arrives in a tool message; then answer using only that result. '
    'Do not use tools for normal conversation.'
)

# --- model ----------------------------------------------------------------------------------------
BASE_MODEL = 'Qwen/Qwen2.5-1.5B-Instruct'  # native <tool_call> support; Qwen2.5-0.5B-Instruct is faster on CPU
OUT_DIR = 'out-saturday'  # fine-tuned model (HF format)
SEED = 1337
IGNORE_INDEX = -100
MODEL_HOST = '127.0.0.1'
MODEL_PORT = 8001
HF_REPO_ENV = 'HF_REPO'  # e.g. your-user/saturday; the fine-tuned model is pushed here so Colab runs can skip training
REMOTE_ENV = ('HF_TOKEN', HF_REPO_ENV)  # the only .env values forwarded to the Colab VM

# --- colab ----------------------------------------------------------------------------------------
EXPORT_DIR = 'export'
LOCAL_ZIP = 'saturday.zip'
REMOTE_ROOT = '/content/saturday'
REMOTE_ZIP = '/content/saturday.zip'
REMOTE_OUT_ZIP = '/content/saturday-out.zip'
REMOTE_LOG = '/content/saturday-model.log'
REMOTE_OK = '__SATURDAY_OK__'  # printed by every remote script on success; IPython swallows exit codes
REMOTE_STARTED = '__SATURDAY_STARTED__'  # first line of every remote script: distinguishes our failures from the CLI's
REMOTE_PACKAGES = ('transformers>=4.45', 'huggingface_hub')  # torch/numpy/requests are preinstalled on Colab
REMOTE_TIMEOUT = 3 * 3600
TRANSIENT_ERRORS = ('WebSocketConnectionClosedException', 'socket is already closed', 'Connection is already closed',
                    'ConnectionResetError', 'TimeoutError')
RETRY_DELAY = 15
UPLOAD_RETRIES = 6  # DNS for a new runtime can lag by a minute or more
ARCHIVE_EXCLUDE = ('venv', '.venv', 'env', '.env', '*venv*', '.git', '.vscode', '.idea', '__pycache__', '.pytest_cache',
                   'node_modules', 'legacy', 'out-*', EXPORT_DIR, 'contacts.json', 'users.json',
                   '*.pyc', '*.zip', '*.mp3', '*.wav', '*.png', '*.jpg')  # secrets and personal data stay local
ARCHIVE_MAX_MB = 20  # anything bigger means a venv or model weights slipped in; the Colab upload API rejects it
CA_BUNDLE_FILE = 'ca-bundle.pem'
SERVER_AUTH_OID = '1.3.6.1.5.5.7.3.1'
SSH_KEYS = ('id_ed25519', 'id_ecdsa')  # the only key types the Colab SSH endpoint accepts
SSH_HOST = 'root@colab'
SSH_OPTIONS = ('StrictHostKeyChecking=no', 'ExitOnForwardFailure=yes', 'ServerAliveInterval=30', 'LogLevel=ERROR')
SESSION_LINE = r'^\[(\S+)\] \S+ \| '  # `colab sessions` prints "[name] endpoint | Hardware: ..." per session

# --- data -----------------------------------------------------------------------------------------
DATA_DIR = 'data'
CONVERSATIONS_PATH = f'{DATA_DIR}/conversations.txt'
CONTACTS_PATH = f'{DATA_DIR}/contacts.json'
SPEAKERS = {'User': 'user', NAME: 'assistant', 'Tool': 'tool', 'Context': 'system'}
SEPARATOR = '---'
ENV_FILE = '.env'

# --- voice ----------------------------------------------------------------------------------------
WHISPER_MODEL = 'base.en'  # tiny.en / base.en / small.en / medium.en
TTS_VOICE = 'en-IN-PrabhatNeural'
SAMPLE_RATE = 16000

# --- conversation ---------------------------------------------------------------------------------
GOODBYE_WORDS = ('bye', 'goodbye', 'good night', 'see you later', 'exit', 'quit')
YES_WORDS = ('yes', 'yeah', 'yep', 'yup', 'sure', 'ok', 'okay', 'go ahead', 'do it', 'allow')
GREETINGS = {(0, 12): 'a warm good morning {title}', (12, 18): 'good afternoon {title}', (18, 24): 'good evening {title}'}

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
