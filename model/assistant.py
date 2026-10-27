import json
import re
import threading
from datetime import datetime

from common.constants import CONTEXT_PROMPT, GOODBYE_WORDS, GUEST_PROMPT, TOOL_PROMPT
from common.utils import contains_any
from model.chat import chat_backend


def build_system_prompt(config, plugins):
    prompt = TOOL_PROMPT.replace('{tools}', plugins.describe()).replace('{platform}', config.platform_name())
    return f"{config.system_prompt}\n{prompt}"


def context_prompt(user, now=None):
    # Not part of fine-tuning: who is here and what time it is change every session.
    now = now or datetime.now()
    who = user.describe() + ('' if user.is_owner else ' ' + GUEST_PROMPT) if user is not None else ''
    return CONTEXT_PROMPT.format(user=who, time=now.strftime('%A %d %B %Y, %I:%M %p')).strip()


class ToolCall:

    PATTERN = re.compile(r'<tool_call>\s*(\{.*?\}|\[.*?\])\s*(?:</tool_call>|$)', re.DOTALL)
    NAME_KEYS = ('name', 'tool', 'function', 'tool_name')
    ARGUMENT_KEYS = ('arguments', 'parameters', 'params', 'args', 'input')

    def __init__(self, name, arguments, error=None):
        self.name = name
        self.arguments = arguments
        self.error = error

    @property
    def raw(self):
        return f'<tool_call>{json.dumps({"name": self.name, "arguments": self.arguments})}</tool_call>'

    @staticmethod
    def loads(text):
        # Small models write Windows paths with single backslashes, which is invalid JSON escaping.
        for candidate in (text, text.replace('\\', '\\\\'), re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        raise ValueError(f"malformed tool call: {text[:200]}")

    @classmethod
    def parse(cls, text):
        match = cls.PATTERN.search(text)
        if not match:
            return None
        try:
            data = cls.loads(match.group(1))
            if isinstance(data, list) and data:
                data = data[0]
            if not isinstance(data, dict):
                raise ValueError('tool call must be an object')
            name = next((data[key] for key in cls.NAME_KEYS if isinstance(data.get(key), str)), None)
            arguments = next((data[key] for key in cls.ARGUMENT_KEYS if isinstance(data.get(key), dict)), None)
            if name is None and len(data) == 1:
                # shorthand like {"weather": {"city": "Ranchi"}}
                name, value = next(iter(data.items()))
                arguments = value if isinstance(value, dict) else None
            if arguments is None:
                arguments = {k: v for k, v in data.items() if k not in cls.NAME_KEYS + cls.ARGUMENT_KEYS}
            return cls(str(name or ''), arguments)
        except ValueError as error:
            return cls('', {}, error=str(error))


class Session:

    def __init__(self, user=None):
        self.user = user  # common.users.User or None
        self.history = []
        self.pending = None  # tool call waiting for the user's permission

    def add(self, role, content):
        self.history.append({'role': role, 'content': content})

    def trim(self, max_turns):
        starts = [i for i, m in enumerate(self.history) if m['role'] == 'user']
        if len(starts) > max_turns:
            del self.history[:starts[-max_turns]]


class Assistant:
    """Generate → parse tool call → run plugin → feed result back, up to max_tool_calls per turn."""

    GIVE_UP = 'Sorry boss, I could not get that done. Could you try again?'

    def __init__(self, config, plugins, log):
        self.config = config
        self.plugins = plugins
        self.log = log
        self.lock = threading.Lock()
        self.chat = chat_backend(config, log).load(self.system_prompt())
        self.log('info', f"model ready ({self.chat.source}) with tools: {', '.join(p.name for p in plugins)}")

    def system_prompt(self):
        return build_system_prompt(self.config, self.plugins)

    def generate(self, session):
        system = f"{self.system_prompt()}\n{context_prompt(session.user)}"
        return self.chat.generate([{'role': 'system', 'content': system}] + session.history)

    @staticmethod
    def is_goodbye(text):
        return contains_any(text, GOODBYE_WORDS)

    def respond(self, session, message):
        with self.lock:
            self.log('user', message)
            if session.pending is not None:
                session.pending = None
                self.record(session, 'denied by user')
            session.add('user', message)
            session.trim(self.config.max_history)
            return self.step(session)

    def resume(self, session, allow):
        with self.lock:
            call, session.pending = session.pending, None
            self.log('user', f"{'allowed' if allow else 'denied'}: {call.name}")
            if allow:
                self.execute(session, self.plugins.get(call.name), call)
            else:
                self.record(session, 'denied by user')
            return self.step(session)

    def step(self, session):
        for _ in range(self.config.max_tool_calls):
            answer = self.generate(session)
            call = ToolCall.parse(answer)
            if call is None:
                session.add('assistant', answer)
                self.log('ai', answer)
                return answer, None
            session.add('assistant', call.raw)
            self.log('tool', f"call {call.raw}")
            try:
                if call.error:
                    raise ValueError(call.error)
                plugin = self.plugins.get(call.name)
                call.arguments = plugin.validate(call.arguments)
            except ValueError as error:
                self.log('error', f"{error} | model wrote: {answer[:300]}")
                self.record(session, f"error: {error}")
                continue
            if plugin.confirm:
                if session.user is not None and not session.user.is_owner:
                    self.log('tool', f"refused {plugin.name} for non-owner {session.user.name}")
                    self.record(session, f"error: only the owner may use {plugin.name}; {session.user.name} is a {session.user.role}")
                    continue
                session.pending = call
                title = (session.user.title if session.user is not None else 'boss').capitalize()
                question = f"{title}, shall I {plugin.summary(call.arguments)}?"
                self.log('wait', question)
                return question, call
            self.execute(session, plugin, call)
        session.add('assistant', self.GIVE_UP)
        self.log('error', f"gave up after {self.config.max_tool_calls} tool calls")
        return self.GIVE_UP, None

    def execute(self, session, plugin, call):
        self.log('tool', f"running {plugin.summary(call.arguments)}")
        try:
            result = str(plugin.run(**call.arguments))
        except Exception as error:
            result = f"error: {type(error).__name__}: {str(error)[:200]}"
        self.log('error' if result.startswith('error:') else 'tool', f"result: {result}")
        self.record(session, result)

    def record(self, session, result):
        session.add('tool', result[:self.config.max_tool_result])
