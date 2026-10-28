"""Who is talking? Asked once at startup (name by voice or keyboard, PIN by keyboard only)."""
import getpass

from saturday.constants import USERS_PATH
from saturday.users import Users, default_owner, guest

ASK_NAME = "Who am I talking to?"
ASK_PIN = 'PIN please'
WRONG_PIN = "That's not it. Let's try again."
MAX_PIN_TRIES = 3


def resolve(users, name):
    """Known user by name/alias, else a guest profile."""
    return users.find(name) or guest(name)


def login(config, io, log):
    """CLI/voice login. Returns a User (owner needs a PIN if one is set; guests never do)."""
    users = Users(config.path(USERS_PATH))
    if not users.users:
        log('info', f"no users in {users.path}; run `saturday adduser` to be recognised. Treating you as the owner.")
        return default_owner(config)
    name = config.user
    while not name:
        io.say(ASK_NAME)
        name = io.listen()
    user = resolve(users, name)
    for attempt in range(MAX_PIN_TRIES if user.needs_pin else 0):
        io.say(ASK_PIN)
        try:
            pin = getpass.getpass(f"{config.name}: {ASK_PIN} ")
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
