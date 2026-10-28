"""llama.cpp backend (llama-cpp-python): quantized GGUF models that run on an ordinary CPU. Inference only; the
persona comes from the system prompt, so pair it with a good instruct model (Qwen2.5, SmolLM2, Ministral, Gemma...)."""
import json
import os
import re

from saturday.constants import GGUF_FILE
from saturday.models import ChatBackend
from saturday.utils import timed, trim_loop


class GGUFChat(ChatBackend):

    def __init__(self, config, log=print):
        super().__init__(config, log)
        self.llama = None

    def load(self, system_prompt=''):
        try:
            from llama_cpp import Llama
        except ImportError:
            raise SystemExit('the gguf backend needs llama-cpp-python: pip install "saturday[gguf]"')
        cfg = self.config
        options = dict(n_ctx=cfg.context_length, n_gpu_layers=cfg.gpu_layers, seed=cfg.seed, verbose=False)
        if cfg.model_name.lower().endswith('.gguf') or os.path.exists(cfg.model_name):
            self.log('model', f"loading {cfg.model_name}")
            self.llama = Llama(model_path=cfg.model_name, **options)
            self.source = cfg.model_name
        else:
            pattern = cfg.model_file or GGUF_FILE
            self.log('model', f"loading {cfg.model_name} ({pattern}) via llama.cpp")
            self.llama = timed(self.log, 'loaded', lambda: Llama.from_pretrained(cfg.model_name, pattern, **options))
            self.source = f"{cfg.model_name}:{os.path.basename(self.llama.model_path)}"
        return self

    def completion_kwargs(self):
        cfg = self.config
        return dict(max_tokens=cfg.max_new_tokens, temperature=cfg.temperature, top_p=0.9,
                    repeat_penalty=cfg.repetition_penalty)

    def complete(self, messages):
        result = self.llama.create_chat_completion(messages=messages, **self.completion_kwargs())
        return result['choices'][0]['message']['content'] or ''

    def generate(self, messages):
        try:
            text = timed(self.log, f"generated ({len(messages)} messages)", lambda: self.complete(messages))
        except Exception as error:
            # Some chat templates reject the `tool` role; retry with tool results spoken by the user.
            if not any(m['role'] == 'tool' for m in messages):
                raise
            self.log('model', f"template rejected tool messages ({type(error).__name__}); retrying as user turns")
            flattened = [dict(m, role='user', content=f"Tool result: {m['content']}") if m['role'] == 'tool' else m
                         for m in messages]
            text = self.complete(flattened)
        return self.tag_tool_call(trim_loop(text.strip()))

    @staticmethod
    def tag_tool_call(text):
        # llama.cpp drops special tokens such as Qwen's <tool_call> when decoding; put the tags back around bare JSON.
        if '<tool_call>' in text or not text.startswith('{'):
            return text
        candidate = re.match(r'\{.*\}', text, re.DOTALL)
        try:
            data = json.loads(candidate.group(0)) if candidate else None
        except json.JSONDecodeError:
            return text
        if isinstance(data, dict) and 'name' in data:
            return f'<tool_call>{json.dumps(data)}</tool_call>'
        return text
