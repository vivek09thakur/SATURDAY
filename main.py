"""Saturday: a personal voice assistant powered by Qwen2.5 with tool calling.

By default the model lives on a Colab GPU (needs `pip install google-colab-cli` and a Google sign-in);
voice and every tool run on this machine. The first run fine-tunes the base model on data/conversations.txt;
set HF_REPO (+ HF_TOKEN) in .env and the result is pushed to the Hub so later runs skip training.

    python main.py                   talk to Saturday (model on Colab)
    python main.py --local           talk to Saturday (model on this machine)
    python main.py --text            keyboard instead of microphone (combinable with --local)
    python main.py --tui             terminal UI with the clock character (add --text for keyboard only)
    python main.py finetune          fine-tune on Colab; --local to do it here
    python main.py model --local     run only the model server (what the Colab VM runs)
    python main.py --key=value       override any field of common.common.Config
"""
import os
import sys

from common.common import Log, configure
from common.utils import greeting, is_yes, load_env

ROOT = os.path.dirname(os.path.abspath(__file__))


def build(config, log):
    from model.assistant import Assistant
    from plugins import Registry
    return Assistant(config, Registry(config), log)


def finetune(config, log):
    config.train = True
    from model.assistant import build_system_prompt
    from model.chat import SaturdayChat
    from plugins import Registry
    SaturdayChat(config, log).load(build_system_prompt(config, Registry(config)))


def model(config, log):
    from model.server import ModelServer
    ModelServer(config, log).serve()


def talk(config, log):
    if config.tui:
        from controls.tui import TUI
        return TUI(config, lambda tui_log: build(config, tui_log), lambda sink: Log(sink=sink)).run()
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


COMMANDS = {'talk': talk, 'finetune': finetune, 'model': model}
REMOTE_COMMANDS = ('talk', 'finetune')  # run on Colab unless --local or --model_url is given


def main():
    load_env()
    argv = sys.argv[1:]
    command = argv[0] if argv and not argv[0].startswith('--') else 'talk'
    if command not in COMMANDS:
        raise SystemExit(f"unknown command {command!r}; choose from {', '.join(COMMANDS)}\n\n{__doc__}")
    flags = [a for a in argv if a.startswith('--')]
    config = configure(flags)
    if command in REMOTE_COMMANDS and not config.local and not config.model_url:
        from model.colab import ColabRunner
        return ColabRunner(config, ROOT).run(command, flags)
    COMMANDS[command](config, Log())


if __name__ == '__main__':
    main()
