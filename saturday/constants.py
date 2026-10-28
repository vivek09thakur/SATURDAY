
PROJECT_FILE = 'saturday.toml'
DATA_DIR = 'data'
CONVERSATIONS_PATH = f'{DATA_DIR}/conversations.txt'
USERS_PATH = f'{DATA_DIR}/users.json'
PLUGIN_DIR = 'plugins'
ENV_FILE = '.env'
OUT_DIR = 'out-adapter'
DEFAULT_REGISTRY = 'saturday.plugins:Registry'

DEFAULT_NAME = 'Assistant'
DEFAULT_PERSONA = (
    'You are {name}, a personal voice assistant created by {author}, your boss. '
    'You are warm, casual and a bit playful, like a close friend. '
    'Your replies are spoken aloud, so answer in one or two short plain sentences: no markdown, no lists, no emojis. '
    'Remember what the user tells you, such as how their day went.'
)
DEFAULT_GUEST_PROMPT = ("They are not your owner: be polite, keep {author}'s personal details private, "
                        'and politely refuse anything that changes this computer or sends messages.')
DEFAULT_GREETINGS = [[0, 'a warm good morning {title}'], [12, 'good afternoon {title}'], [18, 'good evening {title}']]
DEFAULT_GOODBYE_WORDS = ['bye', 'goodbye', 'good night', 'see you later', 'exit', 'quit']
DEFAULT_YES_WORDS = ['yes', 'yeah', 'yep', 'yup', 'sure', 'ok', 'okay', 'go ahead', 'do it', 'allow']
OWNER_TITLE = 'boss'
GUEST_TITLE = 'friend'

CONTEXT_PROMPT = '{user} It is {time}.'
TOOL_PROMPT = (
    'You can use tools. When the user asks for something that needs one, reply with only:\n'
    '<tool_call>{"name": "tool_name", "arguments": {"param": "value"}}</tool_call>\n'
    'Tools:\n{tools}\n'
    'This computer runs {platform}. '
    'The result arrives in a tool message; then answer using only that result. '
    'Do not use tools for normal conversation.'
)
SPEAKER_ROLES = {'User': 'user', 'Assistant': 'assistant', 'Tool': 'tool', 'Context': 'system'}
SEPARATOR = '---'
IGNORE_INDEX = -100

BASE_MODEL = 'mistralai/Ministral-3-3B-Instruct-2512-BF16'
BACKENDS = ('transformers', 'gguf')
GGUF_MODEL = 'Qwen/Qwen2.5-1.5B-Instruct-GGUF'
GGUF_FILE = '*q4_k_m.gguf'
SEED = 1337
MODEL_HOST = '127.0.0.1'
MODEL_PORT = 8001
HF_REPO_ENV = 'HF_REPO'
REMOTE_ENV = ('HF_TOKEN', HF_REPO_ENV)

EXPORT_DIR = 'export'
LOCAL_ZIP = 'saturday-upload.zip'
REMOTE_ROOT = '/content/saturday-run'
REMOTE_PACKAGE_DIR = 'saturday'
REMOTE_PROJECT_DIR = 'project'
REMOTE_ZIP = '/content/saturday-upload.zip'
REMOTE_OUT_ZIP = '/content/saturday-out.zip'
REMOTE_LOG = '/content/saturday-model.log'
REMOTE_OK = '__SATURDAY_OK__'
REMOTE_STARTED = '__SATURDAY_STARTED__'
REMOTE_PACKAGES = ('transformers>=5.0.0', 'peft>=0.15', 'huggingface_hub')
REMOTE_REMOVE = ('torchao',)
REMOTE_TIMEOUT = 3 * 3600
TRANSIENT_ERRORS = ('WebSocketConnectionClosedException', 'socket is already closed', 'Connection is already closed',
                    'ConnectionResetError', 'TimeoutError')
RETRY_DELAY = 15
UPLOAD_RETRIES = 6
ARCHIVE_EXCLUDE = ('venv', '.venv', 'env', '.env', '*venv*', '.git', '.vscode', '.idea', '__pycache__', '.pytest_cache',
                   'node_modules', 'legacy', 'out-*', EXPORT_DIR, 'contacts.json', 'users.json', 'workspace',
                   '*.pyc', '*.zip', '*.mp3', '*.wav', '*.png', '*.jpg', '*.gguf', '*.bin', '*.pt', '*.pkl',
                   '*.safetensors')
ARCHIVE_MAX_MB = 20
CA_BUNDLE_FILE = 'ca-bundle.pem'
SERVER_AUTH_OID = '1.3.6.1.5.5.7.3.1'
SSH_KEYS = ('id_ed25519', 'id_ecdsa')
SSH_HOST = 'root@colab'
SSH_OPTIONS = ('StrictHostKeyChecking=no', 'ExitOnForwardFailure=yes', 'ServerAliveInterval=30', 'LogLevel=ERROR')
SESSION_LINE = r'^\[(\S+)\] \S+ \| '

WHISPER_MODEL = 'base.en'
TTS_VOICE = 'en-IN-PrabhatNeural'
SAMPLE_RATE = 16000
