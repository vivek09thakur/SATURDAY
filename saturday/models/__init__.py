"""Model backends. `chat_backend(config, log)` picks one:

- remote        --model_url is set: generation happens on a model server (saturday/models/server.py), e.g. on Colab
- transformers  Hugging Face model + LoRA adapter (fine-tunes itself on data/conversations.txt when no adapter exists)
- gguf          llama.cpp via llama-cpp-python: quantized models that run on a laptop CPU; inference only
"""


class ChatBackend:

    def __init__(self, config, log=print):
        self.config = config
        self.log = log
        self.source = None

    def load(self, system_prompt=''):
        return self

    def generate(self, messages):
        raise NotImplementedError

    def finetune(self, system_prompt):
        raise SystemExit(f"the {self.config.backend} backend cannot fine-tune; set backend = \"transformers\" in saturday.toml")


def chat_backend(config, log=print):
    if config.model_url:
        from saturday.models.remote import RemoteChat
        return RemoteChat(config, log)
    if config.backend == 'gguf':
        from saturday.models.gguf import GGUFChat
        return GGUFChat(config, log)
    from saturday.models.transformers import TransformersChat
    return TransformersChat(config, log)
