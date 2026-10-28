"""Who is talking to the assistant. Profiles live in data/users.json (gitignored); PINs are stored as salted SHA-256."""
import getpass
import hashlib
import json
import os
import re
import secrets
from dataclasses import dataclass, field

from saturday.constants import GUEST_TITLE, USERS_PATH


@dataclass
class User:
    name: str
    title: str = GUEST_TITLE  # how the assistant addresses them: boss, sir, ma'am, their name...
    role: str = 'guest'  # owner | family | friend | guest
    about: str = ''  # one line the assistant knows about them
    aliases: list = field(default_factory=list)
    pin: str = ''  # 'salt:hash' or '' for no PIN

    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def needs_pin(self):
        return bool(self.pin)

    def matches(self, spoken):
        spoken = normalize(spoken)
        return any(normalize(n) in spoken or spoken in normalize(n) for n in [self.name, *self.aliases] if n)

    def check_pin(self, pin):
        if not self.pin:
            return True
        salt, digest = self.pin.split(':', 1)
        return secrets.compare_digest(hash_pin(pin, salt), digest)

    def describe(self):
        who = f"{self.name} ({self.role}" + (f", {self.about}" if self.about else '') + ')'
        return f"You are talking to {who}. Address them as '{self.title}'."


def normalize(text):
    return re.sub(r'[^a-z ]', '', text.lower()).strip()


def hash_pin(pin, salt):
    return hashlib.sha256(f"{salt}:{pin}".encode('utf-8')).hexdigest()


def encode_pin(pin):
    salt = secrets.token_hex(8)
    return f"{salt}:{hash_pin(pin, salt)}"


def guest(name):
    return User(name=name.strip().title() or 'Guest', title=name.strip().title() or GUEST_TITLE, role='guest',
                about='a guest, not the owner')


def default_owner(config):
    # Used when data/users.json does not exist yet: whoever is at the keyboard is the owner.
    return User(name=config.owner_title.capitalize(), title=config.owner_title, role='owner')


class Users:

    def __init__(self, path=USERS_PATH):
        self.path = path
        self.users = []
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                self.users = [User(**u) for u in json.load(f).get('users', [])]

    def save(self):
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({'users': [u.__dict__ for u in self.users]}, f, indent=2)

    def find(self, spoken):
        for user in self.users:
            if user.matches(spoken):
                return user
        return None

    def owner(self):
        return next((u for u in self.users if u.is_owner), None)

    def add(self, name, title, role, about, pin):
        existing = self.find(name)
        if existing is not None:
            self.users.remove(existing)
        self.users.append(User(name=name, title=title, role=role, about=about, pin=encode_pin(pin) if pin else ''))
        self.save()

    def add_interactive(self, config):
        print(f"Adding a user to {self.path}")
        name = input('Name: ').strip()
        if not name:
            raise SystemExit('a name is required')
        role = (input(f"Role [owner/family/friend/guest] ({'owner' if not self.owner() else 'friend'}): ").strip()
                or ('owner' if not self.owner() else 'friend'))
        default_title = config.owner_title if role == 'owner' else name.split()[0]
        title = input(f"How should {config.name} address them? ({default_title}): ").strip() or default_title
        about = input('One line about them (optional): ').strip()
        pin = getpass.getpass('PIN (Enter for none): ')
        if pin and getpass.getpass('Repeat PIN: ') != pin:
            raise SystemExit('PINs did not match')
        self.add(name, title, role, about, pin)
        print(f"saved {name} as {role}" + (' with a PIN' if pin else ''))
