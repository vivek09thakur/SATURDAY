import json
import os

from common.constants import CONTACTS_PATH


def load_contacts(path=CONTACTS_PATH):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return json.load(f)['contacts']


def find_contact(name, field):
    """Match a spoken name against contacts.json; exact name first, then any contact whose name contains it."""
    wanted = name.lower().strip()
    contacts = [c for c in load_contacts() if c.get(field)]
    for contact in contacts:
        if contact['name'].lower() == wanted:
            return contact
    for contact in contacts:
        if wanted in contact['name'].lower() or contact['name'].lower() in wanted:
            return contact
    known = ', '.join(c['name'] for c in contacts) or 'none'
    raise ValueError(f"no {field} for '{name}'; known contacts: {known}")
