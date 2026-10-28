import fnmatch
import os
import re
import time
import zipfile
from datetime import datetime

from saturday.constants import ENV_FILE


def load_env(path=ENV_FILE):
    if not os.path.exists(path):
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_env(key):
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"{key} is not set; add it to {ENV_FILE}")
    return value


def timed(log, label, func):
    started = time.time()
    result = func()
    log('model', f"{label} in {time.time() - started:.1f}s")
    return result


LOOP = re.compile(r'(.{4,80}?)(?:\1){2,}', re.DOTALL)


def trim_loop(text):
    match = LOOP.search(text)
    if match is None:
        return text
    return text[:match.start() + len(match.group(1))].rstrip(' ,;:-') + '.'


def greeting(config, user=None, now=None):
    hour = (now or datetime.now()).hour
    text = config.greetings[0][1]
    for start, candidate in sorted(config.greetings, key=lambda g: g[0]):
        if hour >= start:
            text = candidate
    return text.format(title=user.title if user is not None else config.owner_title)


def is_yes(config, text):
    words = set(re.findall(r'[a-z]+', text.lower()))
    return (any(all(w in words for w in phrase.split()) for phrase in config.yes_words)
            and 'no' not in words and "don't" not in text.lower())


def contains_any(text, phrases):
    text = text.lower()
    return any(phrase in text for phrase in phrases)


def port_in_use(host, port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((host, port)) == 0


def wait_for_health(url, process=None, attempts=120, interval=1.0):
    import requests
    for _ in range(attempts):
        if process is not None and process.poll() is not None:
            raise SystemExit(f"{process.args[0]} exited with {process.returncode}")
        try:
            if requests.get(f'{url}/health', timeout=2).ok:
                return True
        except requests.RequestException:
            pass
        time.sleep(interval)
    return False


def zip_dir(root, path, exclude=(), prefix=''):
    def excluded(name):
        return any(fnmatch.fnmatch(name, pattern) for pattern in exclude)

    count = 0
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not excluded(d)]
            for filename in filenames:
                if not excluded(filename):
                    full = os.path.join(dirpath, filename)
                    zf.write(full, os.path.join(prefix, os.path.relpath(full, root)))
                    count += 1
    return count
