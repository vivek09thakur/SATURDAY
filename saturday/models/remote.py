"""Forwards generation to a model server (saturday/models/server.py), e.g. one running on a Colab GPU."""
from saturday.models import ChatBackend
from saturday.utils import timed, wait_for_health


class RemoteChat(ChatBackend):

    TIMEOUT = 600

    def __init__(self, config, log=print):
        super().__init__(config, log)
        self.source = config.model_url.rstrip('/')

    def load(self, system_prompt=''):
        self.log('model', f"waiting for model server at {self.source}")
        if not wait_for_health(self.source):
            raise SystemExit(f"no model server at {self.source}")
        return self

    def generate(self, messages):
        import requests
        response = timed(self.log, f"generated remotely ({len(messages)} messages)", lambda: requests.post(
            f'{self.source}/generate', json={'messages': messages}, timeout=self.TIMEOUT))
        response.raise_for_status()
        return response.json()['text']
