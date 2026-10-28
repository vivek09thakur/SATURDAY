"""Command line entry point (`saturday` or `python -m saturday`).

    saturday init my-bot --name=Friday  scaffold a new project
    saturday talk                       talk to it (model on Colab by default)
    saturday talk --local               model on this machine
    saturday talk --text                keyboard instead of microphone
    saturday finetune                   fine-tune on Colab (--local to do it here)
    saturday model --local              run only the model server (what the Colab VM runs)
    saturday adduser                    register who the assistant should recognise
    saturday check                      validate saturday.toml, the training data and the plugins
    saturday --key=value                override any Config field (see saturday/config.py)

Every command except `init` runs inside a project: the nearest folder upwards holding saturday.toml, or --root=path.
"""
import os
import re
import sys
from importlib import resources

from saturday import __version__
from saturday.config import Log, configure, find_project, slugify
from saturday.constants import PROJECT_FILE, USERS_PATH
from saturday.utils import greeting, is_yes, load_env

TEMPLATE_FILES = {  # package template -> path inside the new project
    'saturday.toml': 'saturday.toml',
    'README.md': 'README.md',
    'gitignore': '.gitignore',
    'env.example': '.env.example',
    'conversations.txt': 'data/conversations.txt',
    'users.example.json': 'data/users.example.json',
    'example_plugin.py': 'plugins/example.py',
}


# --- commands --------------------------------------------------------------------------------------------

def build(config, log):
    from saturday.assistant import Assistant
    from saturday.plugins import registry
    return Assistant(config, registry(config), log)


def finetune(config, log):
    config.train = True
    from saturday.assistant import build_system_prompt
    from saturday.models import chat_backend
    from saturday.plugins import registry
    chat_backend(config, log).load(build_system_prompt(config, registry(config)))


def model(config, log):
    from saturday.models.server import ModelServer
    ModelServer(config, log).serve()


def talk(config, log):
    from saturday.assistant import Session
    from saturday.voice import TextIO, VoiceIO
    from saturday.voice.login import login
    assistant = build(config, log)
    io = TextIO(config) if config.text else VoiceIO(config, log)
    session = Session(login(config, io, log))
    io.say(greeting(config, session.user))
    while True:
        text = io.listen()
        if not text:
            continue
        reply, pending = assistant.respond(session, text)
        io.say(reply)
        while pending is not None:
            answer = io.listen()
            if not answer:
                continue
            reply, pending = assistant.resume(session, is_yes(config, answer))
            io.say(reply)
        if assistant.is_goodbye(text):
            break


def adduser(config, log):
    from saturday.users import Users
    Users(config.path(USERS_PATH)).add_interactive(config)


def check(config, log):
    """Load everything that does not need a model: config, plugins, training data."""
    from saturday.assistant import build_system_prompt
    from saturday.models.data import ConversationFile
    from saturday.plugins import registry
    plugins = registry(config)
    print(f"{config.name} by {config.author}; model {config.model_name} ({config.backend})")
    print(f"plugins: {', '.join(p.name for p in plugins) or 'none'}")
    conversations = ConversationFile(config.path(config.data_path), '', config.name).load()
    turns = sum(1 for c in conversations for m in c if m['role'] == 'assistant')
    tools = sum(1 for c in conversations for m in c if m['role'] == 'tool')
    print(f"data: {len(conversations)} conversations, {turns} assistant turns, {tools} tool results in {config.data_path}")
    calls = [m['content'] for c in conversations for m in c if m['role'] == 'assistant' and '<tool_call>' in m['content']]
    names = {match.group(1) for text in calls for match in re.finditer(r'"name":\s*"([^"]+)"', text)}
    unknown = sorted(n for n in names if n not in {p.name for p in plugins})
    if unknown:
        print(f"warning: training data calls tools that are not available: {', '.join(unknown)}")
    print(f"system prompt: {len(build_system_prompt(config, plugins))} characters")
    print('ok')


COMMANDS = {'talk': talk, 'finetune': finetune, 'model': model, 'adduser': adduser, 'check': check}
REMOTE_COMMANDS = ('talk', 'finetune')  # run on Colab unless --local or --model_url is given


# --- init ------------------------------------------------------------------------------------------------

def init(args):
    target = next((a for a in args if not a.startswith('--')), None)
    name = next((a.partition('=')[2] for a in args if a.startswith('--name=')), '')
    author = next((a.partition('=')[2] for a in args if a.startswith('--author=')), '')
    if target is None:
        raise SystemExit('usage: saturday init <folder> [--name=Friday] [--author="Your Name"]')
    name = name or re.sub(r'[-_]+', ' ', os.path.basename(os.path.abspath(target))).title().replace(' ', '')
    author = author or os.environ.get('USERNAME') or os.environ.get('USER') or 'the owner'
    if os.path.exists(os.path.join(target, PROJECT_FILE)):
        raise SystemExit(f"{target} already holds an saturday project")
    values = {'__NAME__': name, '__AUTHOR__': author, '__SLUG__': slugify(name), '__VERSION__': __version__}
    templates = resources.files('saturday') / 'templates'
    for source, destination in TEMPLATE_FILES.items():
        text = (templates / source).read_text(encoding='utf-8')
        for key, value in values.items():
            text = text.replace(key, value)
        path = os.path.join(target, destination)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(f"created {name} in {os.path.abspath(target)}\n")
    print(f"  cd {target}")
    print(f"  saturday adduser          # tell {name} who you are (optional)")
    print("  saturday talk --text      # chat with the keyboard; drop --text for voice")
    print(f"\nThen edit saturday.toml (persona, model, voice) and data/conversations.txt (how {name} talks),")
    print("and run `saturday finetune` to teach the model. Secrets go in .env (see .env.example).")


# --- main ------------------------------------------------------------------------------------------------

def trust_os_certificates():
    # Behind a TLS-inspecting proxy the corporate CA is only in the OS store; make Python's ssl use it.
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    # Colab streams progress bars with block glyphs; a redirected Windows stdout is cp1252 and would crash on them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='replace')
    command = argv[0] if argv and not argv[0].startswith('--') else 'talk'
    if command in ('version', '--version'):
        return print(f"saturday {__version__}")
    if command in ('help', '--help', '-h'):
        return print(__doc__)
    if command == 'init':
        return init(argv[1:])
    if command not in COMMANDS:
        raise SystemExit(f"unknown command {command!r}; choose from {', '.join(COMMANDS)}, init\n\n{__doc__}")
    flags = [a for a in argv if a.startswith('--')]
    root = next((a.partition('=')[2] for a in flags if a.startswith('--root=')), None) or find_project()
    if root is None:
        raise SystemExit(f"no {PROJECT_FILE} found here or in a parent folder. Create a project with `saturday init my-bot`, "
                         "or run from inside one (or pass --root=path).")
    root = os.path.abspath(root)
    os.chdir(root)  # every project path (data/, plugins/, .env, out dir) is relative to the project
    load_env()
    trust_os_certificates()
    config = configure([f for f in flags if not f.startswith('--root=')], root)
    if command in REMOTE_COMMANDS and config.runs_remote():
        from saturday.colab import ColabRunner
        return ColabRunner(config, root).run(command, flags)
    COMMANDS[command](config, Log())


if __name__ == '__main__':
    main()