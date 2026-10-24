import os
import platform
import sys
import time
from ast import literal_eval
from dataclasses import dataclass, field, fields

from common.constants import (BASE_MODEL, CONVERSATIONS_PATH, HF_REPO_ENV, MODEL_PORT, OUT_DIR, PERSONA,
                              REMOTE_TIMEOUT, SAMPLE_RATE, SEED, TTS_VOICE, WHISPER_MODEL)


def default_device():
    try:
        import torch
    except ImportError:
        return 'cpu'
    return 'cuda' if torch.cuda.is_available() else 'cpu'


@dataclass
class Config:
    # where the model runs
    local: bool = False  # run the model on this machine instead of a Colab GPU
    model_url: str = ''  # when set, generation is delegated to a model server at this URL
    model_port: int = MODEL_PORT
    hf_repo: str = field(default_factory=lambda: os.environ.get(HF_REPO_ENV, ''))
    platform: str = ''  # OS the tools run on; defaults to this machine (set when the model runs elsewhere)
    # colab
    gpu: str = 'T4'  # T4, L4, A100 or '' for a CPU runtime
    session: str = 'saturday'
    keep: bool = False  # leave the VM running afterwards
    reuse: bool = False  # attach to an existing session instead of creating one
    remote_timeout: int = REMOTE_TIMEOUT
    # model
    model_name: str = BASE_MODEL
    out_dir: str = OUT_DIR
    data_path: str = CONVERSATIONS_PATH
    train: bool = False  # force a fine-tune even if a trained model exists
    train_layers: int = 6  # only the last N transformer blocks are trained; 0 = all
    epochs: int = 3
    learning_rate: float = 1e-4
    batch_size: int = 1
    accumulation: int = 2  # optimizer step every N batches
    max_length: int = 1024
    temperature: float = 0.3
    repetition_penalty: float = 1.15
    no_repeat_ngram_size: int = 6
    max_new_tokens: int = 200
    seed: int = SEED
    device: str = field(default_factory=default_device)
    # assistant
    system_prompt: str = PERSONA
    max_history: int = 6  # user turns kept in context
    max_tool_calls: int = 3  # per user turn
    max_tool_result: int = 1500
    # voice
    text: bool = False  # keyboard instead of microphone and speaker
    whisper_model: str = WHISPER_MODEL
    voice: str = TTS_VOICE
    sample_rate: int = SAMPLE_RATE
    max_record_seconds: float = 12.0
    silence_seconds: float = 1.2  # stop recording after this much silence once speech began
    silence_threshold: float = 0.01  # RMS below this counts as silence
    listen_timeout: float = 8.0  # give up if nobody speaks for this long

    def platform_name(self):
        return self.platform or f"{platform.system()} {platform.release()}"


def configure(argv=None):
    config = Config()
    keys = {f.name for f in fields(config)}
    for arg in sys.argv[1:] if argv is None else argv:
        if not arg.startswith('--'):
            continue
        key, has_value, raw = arg[2:].partition('=')
        if key not in keys:
            raise SystemExit(f"unknown option --{key}")
        current = getattr(config, key)
        if not has_value and isinstance(current, bool):
            value = True
        else:
            try:
                value = literal_eval(raw)
            except (ValueError, SyntaxError):
                value = raw
            if current is not None and not isinstance(value, type(current)):
                value = type(current)(value)
        setattr(config, key, value)
    return config


class Log:

    def __init__(self, quiet=False):
        self.quiet = quiet

    def __call__(self, kind, text):
        if self.quiet and kind in ('model',):
            return
        text = ' '.join(str(text).split())[:400]
        print(f"[{time.strftime('%H:%M:%S')}] [{kind}] {text}", flush=True)
