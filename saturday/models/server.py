import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from saturday.assistant import build_system_prompt
from saturday.constants import MODEL_HOST
from saturday.models import chat_backend


class ModelServer:
    """Minimal HTTP front for a chat backend: GET /health, POST /generate {"messages": [...]} -> {"text": ...}.
    Meant to run next to the GPU (Colab) while the assistant, voice and tools run on the user's machine."""

    def __init__(self, config, log):
        from saturday.plugins import registry
        self.config = config
        self.log = log
        self.lock = threading.Lock()
        self.chat = chat_backend(config, log).load(build_system_prompt(config, registry(config)))

    def generate(self, messages):
        with self.lock:
            return self.chat.generate(messages)

    def serve(self):
        server = ThreadingHTTPServer((MODEL_HOST, self.config.model_port), self.handler())
        self.log('info', f"model server ready ({self.chat.source}) on http://{MODEL_HOST}:{self.config.model_port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()

    def handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):

            def log_message(self, fmt, *args):
                outer.log('http', fmt % args)

            def reply(self, status, payload):
                body = json.dumps(payload).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == '/health':
                    return self.reply(200, {'status': 'ok', 'source': outer.chat.source})
                self.reply(404, {'error': 'not found'})

            def do_POST(self):
                if self.path != '/generate':
                    return self.reply(404, {'error': 'not found'})
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    data = json.loads(self.rfile.read(length) or b'{}')
                    messages = data.get('messages')
                    if not isinstance(messages, list) or not messages or len(messages) > 200:
                        raise ValueError('messages must be a non-empty list')
                    for message in messages:
                        if not isinstance(message, dict) or not isinstance(message.get('content'), str):
                            raise ValueError('each message needs a string content')
                except (ValueError, json.JSONDecodeError) as error:
                    return self.reply(400, {'error': str(error)})
                try:
                    self.reply(200, {'text': outer.generate(messages)})
                except Exception as error:
                    outer.log('error', f"{type(error).__name__}: {error}")
                    self.reply(500, {'error': type(error).__name__})

        return Handler
