import os
import platform
import subprocess
from datetime import datetime

from plugins import Plugin


class CurrentTime(Plugin):
    name = 'current_time'
    description = 'Get the current date and time.'

    def run(self):
        return datetime.now().strftime('%A, %d %B %Y, %I:%M %p')


class SystemInfo(Plugin):
    name = 'system_info'
    description = 'Get the operating system, computer name and user name.'

    def run(self):
        return (f"{platform.system()} {platform.release()} ({platform.machine()}), "
                f"computer {platform.node()}, user {os.environ.get('USERNAME') or os.environ.get('USER', '')}")


class CloseTab(Plugin):
    name = 'close_tab'
    description = 'Close the current browser tab.'

    def run(self):
        import pyautogui
        pyautogui.hotkey('ctrl', 'w')
        return 'closed the current tab'


class Shutdown(Plugin):
    name = 'shutdown'
    description = 'Shut down this computer.'
    confirm = True

    def summary(self, arguments):
        return 'shut down the computer'

    def run(self):
        command = ['shutdown', '/s', '/t', '10'] if os.name == 'nt' else ['shutdown', '-h', 'now']
        subprocess.run(command, check=True)
        return 'shutting down in 10 seconds'
