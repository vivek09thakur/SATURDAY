import asyncio
import sys
import threading
import types

sys.stdout.reconfigure(encoding='utf-8')
for name in ['torch', 'transformers', 'torch.utils', 'torch.utils.data']:
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules['torch'].cuda = types.SimpleNamespace(is_available=lambda: False)

from common.common import Config, Log
from controls import tui
from model import server
import main


class FakeChat:
    source = 'fake'

    def generate(self, messages):
        last = messages[-1]
        if last['role'] == 'user' and 'time' in last['content']:
            return '<tool_call>{"name": "current_time", "arguments": {}}</tool_call>'
        if last['role'] == 'tool':
            return f"Boss, {last['content']} [and brackets] survive"
        return f"Echo: {last['content']}"


srv = server.ModelServer.__new__(server.ModelServer)
srv.config, srv.log, srv.lock, srv.chat = Config(), lambda k, t: None, threading.Lock(), FakeChat()
threading.Thread(target=server.ThreadingHTTPServer(('127.0.0.1', 8011), srv.handler()).serve_forever, daemon=True).start()
config = Config(model_url='http://127.0.0.1:8011', text=True, tui=True)
app = tui.SaturdayApp(config, lambda log: main.build(config, log), lambda sink: Log(sink=sink))


async def drive():
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(1.0)
        await pilot.press('ctrl+t')
        for ch in 'what time is it':
            await pilot.press(ch if ch != ' ' else 'space')
        await pilot.press('enter')
        await pilot.pause(0.6)
        typing = app.query_one('#typing', tui.Static)
        print('mid-typing visible:', typing.has_class('on'), '| typewriter:', app.typewriter and app.typewriter[1], 'chars')
        await pilot.pause(3.0)
        log = app.query_one('#log', tui.RichLog)
        print('after:', typing.has_class('on'), '| log lines:', len(log.lines))
        app.exit()

asyncio.run(drive())
print('exited; error =', app.error)
