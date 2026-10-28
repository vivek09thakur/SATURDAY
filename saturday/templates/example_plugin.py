"""An example tool. Any Plugin subclass in this folder is available to the model; delete this file if you don't want it.

The model calls a tool by writing  <tool_call>{"name": "roll_dice", "arguments": {"sides": "20"}}</tool_call>
and then answers from whatever run() returns (a string). Keep return values short and plain; the model reads them.
Teach the model when to use a tool by adding an example to data/conversations.txt.
"""
import random

from saturday.plugins import Plugin


class RollDice(Plugin):
    name = 'roll_dice'
    description = 'Roll a die with the given number of sides.'
    parameters = {'sides': 'number of sides (default 6)'}
    required = ()  # names from `parameters` that must be present
    confirm = False  # True = ask the owner before running (and refuse everyone else)

    def run(self, sides='6'):
        try:
            sides = max(2, int(sides))
        except ValueError:
            sides = 6
        return f"rolled a {random.randint(1, sides)} on a {sides}-sided die"
