"""Saturday: a local voice assistant powered by SmolLM2 with tool calling.

    python main.py                 talk to Saturday (microphone + speaker)
    python main.py --text          chat from the keyboard
    python main.py finetune        fine-tune the base model on data/conversations.txt
    python main.py --key=value     override any field of common.common.Config
"""
import sys

from common.common import Log, configure
from common.utils import greeting, is_yes, load_env


def build(config, log):
    from model.assistant import Assistant
    from plugins import Registry
    return Assistant(config, Registry(config), log)


def finetune(config, log):
    config.train = True
    build(config, log)


def talk(config, log):
    from controls.voice import TextIO, VoiceIO
    from model.assistant import Session
    assistant = build(config, log)
    io = TextIO() if config.text else VoiceIO(config, log)
    session = Session()
    io.say(greeting())
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
            reply, pending = assistant.resume(session, is_yes(answer))
            io.say(reply)
        if assistant.is_goodbye(text):
            break


COMMANDS = {'talk': talk, 'finetune': finetune}


def main():
    load_env()
    argv = sys.argv[1:]
    command = argv[0] if argv and not argv[0].startswith('--') else 'talk'
    if command not in COMMANDS:
        raise SystemExit(f"unknown command {command!r}; choose from {', '.join(COMMANDS)}\n\n{__doc__}")
    config = configure([a for a in argv if a.startswith('--')])
    COMMANDS[command](config, Log())


if __name__ == '__main__':
    main()
