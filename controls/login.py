"""Who is talking? Asked once at startup (name by voice or keyboard, PIN by keyboard only)."""
import getpass

from common.constants import NAME
from common.users import Users, guest

ASK_NAME = "Who am I talking to?"
ASK_PIN = 'PIN please'
WRONG_PIN = "That's not it. Let's try again."
MAX_PIN_TRIES = 3


def resolve(users, name):
    """Known user by name/alias, else a guest profile."""
    return users.find(name) or guest(name)


def login(config, io, log):
    """CLI/voice login. Returns a User (owner needs a PIN if one is set; guests never do)."""
    users = Users()
    if not users.users:
        log('info', f"no users in {users.path}; run `python main.py adduser` to be recognised. Treating you as the owner.")
        from common.users import User
        from common.constants import OWNER_TITLE
        return User(name='Boss', title=OWNER_TITLE, role='owner')
    name = config.user
    while not name:
        io.say(ASK_NAME)
        name = io.listen()
    user = resolve(users, name)
    for attempt in range(MAX_PIN_TRIES if user.needs_pin else 0):
        io.say(ASK_PIN)
        try:
            pin = getpass.getpass(f"{NAME}: {ASK_PIN} ")
        except (EOFError, KeyboardInterrupt):
            pin = ''
        if user.check_pin(pin):
            break
        log('error', f"wrong PIN for {user.name} ({attempt + 1}/{MAX_PIN_TRIES})")
        if attempt + 1 < MAX_PIN_TRIES:
            io.say(WRONG_PIN)
    else:
        if user.needs_pin:
            log('info', f"{user.name} failed the PIN; continuing as a guest")
            user = guest(user.name)
    log('info', f"logged in: {user.name} ({user.role})")
    return user
