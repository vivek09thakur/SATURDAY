"""Headless checks: no model, no microphone. Run with `python -m unittest`."""
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from unittest import mock

from saturday.assistant import Assistant, Session, ToolCall, build_system_prompt, context_prompt
from saturday.cli import main
from saturday.config import Config, configure, find_project
from saturday.models.data import ConversationFile
from saturday.models.gguf import GGUFChat
from saturday.plugins import Plugin, Registry, registry
from saturday.users import User, guest
from saturday.utils import greeting, is_yes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SATURDAY = os.path.join(ROOT, 'examples', 'saturday')


class ScaffoldTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_init_creates_a_loadable_project(self):
        target = os.path.join(self.tmp, 'my-bot')
        with mock.patch('builtins.print'):
            main(['init', target, '--name=Friday', '--author=Jane Doe'])
        self.assertEqual(find_project(os.path.join(target, 'data')), os.path.abspath(target))
        config = configure([], target)
        self.assertEqual((config.name, config.author, config.backend), ('Friday', 'Jane Doe', 'transformers'))
        self.assertIn('You are Friday, a personal voice assistant created by Jane Doe', config.persona_text())
        with open(os.path.join(target, 'data', 'conversations.txt'), encoding='utf-8') as f:
            self.assertNotIn('__NAME__', f.read())
        plugins = registry(config)
        self.assertEqual([p.name for p in plugins], ['roll_dice'])  # the example plugin, discovered from plugins/
        conversations = ConversationFile(config.path(config.data_path), 'SYS', config.name).load()
        self.assertGreater(len(conversations), 10)
        for conversation in conversations:
            self.assertEqual(conversation[0]['role'], 'system')
            self.assertTrue(conversation[0]['content'].startswith('SYS\nYou are talking to'))
            self.assertIn('assistant', {m['role'] for m in conversation})
        with mock.patch('builtins.print') as printed:
            os.chdir(target)
            main(['check', '--local'])
        lines = [str(c.args[0]) for c in printed.call_args_list]
        self.assertIn('ok', lines)
        self.assertFalse(any('warning' in line for line in lines), lines)

    def test_init_refuses_to_overwrite(self):
        target = os.path.join(self.tmp, 'bot')
        with mock.patch('builtins.print'):
            main(['init', target])
        with self.assertRaises(SystemExit):
            main(['init', target])


class ConfigTest(unittest.TestCase):

    def test_toml_sections_and_flags(self):
        config = configure(['--temperature=0.7', '--text'], SATURDAY)
        self.assertEqual(config.name, 'Saturday')
        self.assertEqual(config.model_name, 'mistralai/Ministral-3-3B-Instruct-2512-BF16')
        self.assertEqual(config.session_name(), 'saturday')
        self.assertEqual(config.temperature, 0.7)
        self.assertTrue(config.text)
        self.assertTrue(config.runs_remote())
        self.assertFalse(configure(['--local'], SATURDAY).runs_remote())
        self.assertFalse(configure(['--backend=gguf'], SATURDAY).runs_remote())

    def test_unknown_setting_is_rejected(self):
        with self.assertRaises(SystemExit):
            configure(['--nope=1'], SATURDAY)
        with self.assertRaises(SystemExit):
            configure(['--backend=magic'], SATURDAY)

    def test_app_table_becomes_attributes_and_flags(self):
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, 'saturday.toml'), 'w', encoding='utf-8') as f:
                f.write('[assistant]\nname = "App"\n[app]\nworkspace = "work"\nport = 8000\nweb = false\n'
                        '[plugins]\nregistry = "saturday.plugins:Registry"\n[colab]\nexclude = ["docs"]\n')
            config = configure(['--port=9000', '--web'], tmp)
            self.assertEqual((config.workspace, config.port, config.web), ('work', 9000, True))
            self.assertEqual(config.archive_exclude, ['docs'])
            with self.assertRaises(AttributeError):
                config.missing_setting
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_greetings_and_yes(self):
        config = Config(name='Bot')
        self.assertEqual(greeting(config, None, datetime(2026, 1, 1, 8)), 'a warm good morning boss')
        self.assertEqual(greeting(config, User('Ann', title="ma'am"), datetime(2026, 1, 1, 20)), "good evening ma'am")
        self.assertTrue(is_yes(config, 'yeah go ahead'))
        self.assertFalse(is_yes(config, 'no, do not'))


class PromptTest(unittest.TestCase):

    def test_context_matches_training_wording(self):
        config = Config(name='Saturday', author='Vivek Thakur')
        owner = User('Vivek', title='boss', role='owner', about='your creator')
        line = context_prompt(config, owner, datetime(2026, 11, 2, 9, 12))
        self.assertEqual(line, "You are talking to Vivek (owner, your creator). Address them as 'boss'. "
                               'It is Monday 02 November 2026, 09:12 AM.')
        line = context_prompt(config, guest('rahul'), datetime(2026, 11, 3, 18, 30))
        self.assertIn("keep Vivek Thakur's personal details private", line)

    def test_system_prompt_without_tools(self):
        config = configure([], SATURDAY)
        plugins = registry(config)
        self.assertEqual(len(plugins), 0)
        prompt = build_system_prompt(config, plugins)
        self.assertTrue(prompt.startswith('You are Saturday'))
        self.assertIn('<tool_call>', prompt)

    def test_saturday_data_is_persona_only(self):
        config = configure([], SATURDAY)
        conversations = ConversationFile(config.path(config.data_path), '', config.name).load()
        self.assertEqual(len(conversations), 39)
        for conversation in conversations:
            self.assertTrue(conversation[0]['content'].startswith('You are talking to'))
            self.assertFalse(any(m['role'] == 'tool' for m in conversation))


class FakeChat:

    def __init__(self, replies):
        self.replies = list(replies)
        self.source = 'fake'

    def load(self, system_prompt=''):
        return self

    def generate(self, messages):
        return self.replies.pop(0)


class Echo(Plugin):
    name = 'echo'
    description = 'Echo text.'
    parameters = {'text': 'what to echo'}
    required = ('text',)

    def run(self, text, tag=''):
        return f"{tag}{text}"


class HookedAssistant(Assistant):

    def __init__(self, config, plugins, log, replies):
        self.replies = replies
        self.notes = []
        super().__init__(config, plugins, log)

    def load_chat(self):
        return FakeChat(self.replies)

    def run_arguments(self, session, plugin):
        return {'tag': f"[{session.id}] "}

    def note(self, session, kind, plugin, call, result=None):
        self.notes.append((kind, call.name, result))


class AssistantTest(unittest.TestCase):

    def test_tool_loop_with_hooks(self):
        config = Config(name='Bot')
        plugins = Registry(config)
        plugins.plugins['echo'] = Echo(config)
        assistant = HookedAssistant(config, plugins, lambda kind, text: None, [
            '<tool_call>{"name": "echo", "arguments": {"text": "hi"}}</tool_call>', 'Echoed, boss.'])
        session = Session(session_id='s1')
        reply, pending = assistant.respond(session, 'echo hi')
        self.assertEqual((reply, pending), ('Echoed, boss.', None))
        self.assertEqual(session.history[-2], {'role': 'tool', 'content': '[s1] hi'})
        self.assertEqual(assistant.notes, [('tool', 'echo', '[s1] hi')])

    def test_unknown_tool_is_reported_to_the_model(self):
        config = Config(name='Bot')
        assistant = HookedAssistant(config, Registry(config), lambda kind, text: None, [
            '<tool_call>{"name": "nope", "arguments": {}}</tool_call>', 'Sorry boss.'])
        reply, _ = assistant.respond(Session(), 'do it')
        self.assertEqual(reply, 'Sorry boss.')
        self.assertEqual(assistant.notes[0][:2], ('error', 'nope'))


class ToolCallTest(unittest.TestCase):

    def test_parse_variants(self):
        tagged = ToolCall.parse('<tool_call>{"name": "weather", "arguments": {"city": "Ranchi"}}</tool_call>')
        self.assertEqual((tagged.name, tagged.arguments), ('weather', {'city': 'Ranchi'}))
        self.assertTrue(tagged.id)
        bare = ToolCall.parse('{"name": "weather", "arguments": {"city": "Ranchi"}}')
        self.assertEqual(bare.name, 'weather')
        self.assertIsNone(ToolCall.parse('Just a sentence boss.'))
        self.assertIsNone(ToolCall.parse('{"mood": "happy"}'))
        shorthand = ToolCall.parse('<tool_call>{"weather": {"city": "Delhi"}}</tool_call>')
        self.assertEqual((shorthand.name, shorthand.arguments), ('weather', {'city': 'Delhi'}))

    def test_gguf_retags_bare_json(self):
        text = GGUFChat.tag_tool_call('{"name": "open_website", "arguments": {"site": "github"}}')
        self.assertTrue(text.startswith('<tool_call>') and text.endswith('</tool_call>'))
        self.assertEqual(GGUFChat.tag_tool_call('Hello boss.'), 'Hello boss.')
        self.assertEqual(json.loads(GGUFChat.tag_tool_call('{"name": "x", "arguments": {}}')[11:-12])['name'], 'x')


if __name__ == '__main__':
    unittest.main()