"""Project configuration: defaults → the project's saturday.toml → --key=value flags.

saturday.toml sections map onto the flat Config below: a key `k` in section `[s]` sets the field `s_k` if it exists,
otherwise `k` (so `[model] name` → model_name, `[voice] voice` → voice, `[assistant] name` → name).
The `[app]` table is free-form: its keys become attributes too (config.workspace, --workspace=...), which is how an
application built on Saturday carries its own settings without subclassing.
"""
import os
import platform
import re
import time
import tomllib
from ast import literal_eval
from dataclasses import dataclass, field, fields

from saturday.constants import (BASE_MODEL, CONVERSATIONS_PATH, DEFAULT_GOODBYE_WORDS, DEFAULT_GREETINGS,
                                DEFAULT_GUEST_PROMPT, DEFAULT_NAME, DEFAULT_PERSONA, DEFAULT_REGISTRY,
                                DEFAULT_YES_WORDS, GUEST_TITLE, HF_REPO_ENV, MODEL_PORT, OUT_DIR, OWNER_TITLE,
                                PLUGIN_DIR, PROJECT_FILE, REMOTE_TIMEOUT, SAMPLE_RATE, SEED, TTS_VOICE, WHISPER_MODEL)

ALIASES = {'plugins.dirs': 'plugin_dirs', 'plugins.registry': 'registry', 'colab.exclude': 'archive_exclude'}
APP_SECTION = 'app'


def default_device():
    try:
        import torch
    except ImportError:
        return 'cpu'
    return 'cuda' if torch.cuda.is_available() else 'cpu'


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'assistant'


@dataclass
class Config:
    # [assistant] who the assistant is
    root: str = '.'  # project directory (where saturday.toml lives); every other path is relative to it
    name: str = DEFAULT_NAME
    author: str = 'the owner'
    persona: str = DEFAULT_PERSONA  # system prompt; {name} and {author} are filled in
    guest_prompt: str = DEFAULT_GUEST_PROMPT  # added to the context line for anyone who is not the owner
    owner_title: str = OWNER_TITLE  # how the owner is addressed (boss, sir, ...)
    guest_title: str = GUEST_TITLE
    greetings: list = field(default_factory=lambda: [list(g) for g in DEFAULT_GREETINGS])  # [[from_hour, text], ...]
    goodbye_words: list = field(default_factory=lambda: list(DEFAULT_GOODBYE_WORDS))
    yes_words: list = field(default_factory=lambda: list(DEFAULT_YES_WORDS))
    user: str = ''  # who is talking (name from data/users.json); asked at startup when empty
    max_history: int = 6  # user turns kept in context
    max_tool_calls: int = 3  # per user turn
    max_tool_result: int = 1500
    # where the model runs
    local: bool = False  # run the model on this machine instead of a Colab GPU
    model_url: str = ''  # when set, generation is delegated to a model server at this URL
    model_port: int = MODEL_PORT
    hf_repo: str = field(default_factory=lambda: os.environ.get(HF_REPO_ENV, ''))
    platform: str = ''  # OS the tools run on; defaults to this machine (set when the model runs elsewhere)
    # [colab]
    gpu: str = 'T4'  # T4, L4, A100 or '' for a CPU runtime
    session: str = ''  # Colab session name; defaults to the assistant's name
    keep: bool = False  # leave the VM running afterwards
    reuse: bool = False  # attach to an existing session instead of creating one
    remote_timeout: int = REMOTE_TIMEOUT
    archive_exclude: list = field(default_factory=list)  # extra file/folder patterns kept out of the Colab upload
    # [model]
    backend: str = 'transformers'  # transformers (HF model + LoRA fine-tune) | gguf (llama.cpp, inference only, CPU-friendly)
    model_name: str = BASE_MODEL  # HF repo id or local path; for gguf a repo holding .gguf files or a .gguf path
    model_file: str = ''  # gguf only: file name or glob inside the repo (default: a Q4_K_M quant)
    out_dir: str = OUT_DIR
    data_path: str = CONVERSATIONS_PATH
    train: bool = False  # force a fine-tune even if a trained adapter exists
    lora_rank: int = 16  # LoRA on attention + MLP projections of the language model
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    epochs: int = 3
    learning_rate: float = 2e-4
    batch_size: int = 1
    accumulation: int = 2  # optimizer step every N batches
    max_length: int = 1024
    context_length: int = 4096  # gguf: prompt + answer window
    gpu_layers: int = -1  # gguf: layers offloaded to the GPU when llama.cpp was built with GPU support (-1 = all)
    temperature: float = 0.3
    repetition_penalty: float = 1.15
    no_repeat_ngram_size: int = 6
    max_new_tokens: int = 200
    seed: int = SEED
    device: str = field(default_factory=default_device)
    # [plugins]
    plugin_dirs: list = field(default_factory=lambda: [PLUGIN_DIR])  # project folders with Plugin subclasses
    registry: str = DEFAULT_REGISTRY  # `module:callable(config)` returning the tool registry (apps swap in their own)
    # [voice]
    text: bool = False  # keyboard instead of microphone and speaker
    whisper_model: str = WHISPER_MODEL
    voice: str = TTS_VOICE
    sample_rate: int = SAMPLE_RATE
    max_record_seconds: float = 12.0
    silence_seconds: float = 1.2  # stop recording after this much silence once speech began
    silence_threshold: float = 0.01  # RMS below this counts as silence
    listen_timeout: float = 8.0  # give up if nobody speaks for this long
    # [app] free-form settings of the application built on Saturday
    app: dict = field(default_factory=dict)

    def __getattr__(self, name):
        # Only reached for attributes that are not dataclass fields: look in the [app] table.
        app = self.__dict__.get('app') or {}
        if name in app:
            return app[name]
        raise AttributeError(f"{type(self).__name__} has no setting {name!r}; add it to [{APP_SECTION}] in {PROJECT_FILE}")

    def platform_name(self):
        return self.platform or f"{platform.system()} {platform.release()}"

    def path(self, relative):
        """Project-relative path made absolute (data files, out_dir, user lists)."""
        return relative if os.path.isabs(relative) else os.path.join(self.root, relative)

    def persona_text(self):
        return self.persona.replace('{name}', self.name).replace('{author}', self.author).strip()

    def guest_text(self):
        return self.guest_prompt.replace('{name}', self.name).replace('{author}', self.author).strip()

    def session_name(self):
        return self.session or slugify(self.name)

    def runs_remote(self):
        # Colab is only worth it for the transformers backend; gguf exists precisely to run on this machine.
        return not self.local and not self.model_url and self.backend == 'transformers'


def find_project(start=None):
    """Nearest directory at or above `start` holding saturday.toml, or None."""
    path = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(path, PROJECT_FILE)):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def load_toml(root):
    path = os.path.join(root, PROJECT_FILE)
    if not os.path.exists(path):
        return {}
    with open(path, 'rb') as f:
        return tomllib.load(f)


def apply_toml(config, data, keys):
    for section, values in data.items():
        if not isinstance(values, dict):
            raise SystemExit(f"{PROJECT_FILE}: top-level '{section}' must be a table like [{section}]")
        if section == APP_SECTION:
            config.app.update(values)
            continue
        for key, value in values.items():
            name = ALIASES.get(f'{section}.{key}') or (f'{section}_{key}' if f'{section}_{key}' in keys else key)
            if name not in keys or name == APP_SECTION:
                raise SystemExit(f"{PROJECT_FILE}: unknown setting {key!r} in [{section}]")
            setattr(config, name, value)


def coerce(raw, current):
    try:
        value = literal_eval(raw)
    except (ValueError, SyntaxError):
        value = raw
    if current is not None and not isinstance(value, type(current)):
        value = type(current)(value)
    return value


def apply_flags(config, flags, keys):
    for arg in flags:
        if not arg.startswith('--'):
            continue
        key, has_value, raw = arg[2:].partition('=')
        if key in keys and key != APP_SECTION:
            target, current = config, getattr(config, key)
        elif key in config.app:
            target, current = config.app, config.app[key]
        else:
            raise SystemExit(f"unknown option --{key}")
        value = True if not has_value and isinstance(current, bool) else coerce(raw, current)
        if target is config:
            setattr(config, key, value)
        else:
            config.app[key] = value


def configure(flags=(), root=None):
    """Config for the project at `root` (default: found from the working directory) with `--key=value` overrides."""
    config = Config()
    keys = {f.name for f in fields(config)}
    root = root or find_project()
    if root:
        config.root = root
        apply_toml(config, load_toml(root), keys)
    apply_flags(config, flags, keys)
    if config.backend not in ('transformers', 'gguf'):
        raise SystemExit(f"unknown model backend {config.backend!r}; use transformers or gguf")
    return config


class Log:

    def __init__(self, quiet=False, sink=None):
        self.quiet = quiet
        self.sink = sink  # (kind, text) -> None; default prints

    def __call__(self, kind, text):
        if self.quiet and kind in ('model',):
            return
        text = ' '.join(str(text).split())[:400]
        if self.sink is not None:
            return self.sink(kind, text)
        print(f"[{time.strftime('%H:%M:%S')}] [{kind}] {text}", flush=True)
