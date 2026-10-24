import importlib
import json
import pkgutil


class Plugin:
    """A tool the model can call. Subclass in any module under plugins/ and it is discovered automatically."""

    name = ''
    description = ''
    parameters = {}  # name -> description
    required = ()
    confirm = False  # ask the user before running

    def __init__(self, config):
        self.config = config

    @classmethod
    def describe(cls):
        return f"- {cls.name}({', '.join(cls.parameters)}): {cls.description}"

    def summary(self, arguments):
        return f"{self.name.replace('_', ' ')} {json.dumps(arguments)}"

    def validate(self, arguments):
        if not isinstance(arguments, dict):
            raise ValueError('arguments must be an object')
        # Small models invent argument names; keep the known ones rather than failing the whole call.
        arguments = {key: str(value) for key, value in arguments.items() if key in self.parameters}
        missing = [key for key in self.required if not arguments.get(key)]
        if missing:
            raise ValueError(f"missing arguments: {', '.join(missing)}")
        return arguments

    def run(self, **arguments):
        raise NotImplementedError


class Registry:

    def __init__(self, config):
        self.plugins = {}
        for module_info in pkgutil.iter_modules(__path__):
            importlib.import_module(f'{__name__}.{module_info.name}')
        for cls in self.subclasses(Plugin):
            if cls.name:
                self.plugins[cls.name] = cls(config)

    @classmethod
    def subclasses(cls, base):
        for sub in base.__subclasses__():
            yield sub
            yield from cls.subclasses(sub)

    def describe(self):
        return '\n'.join(type(p).describe() for p in self.plugins.values())

    def get(self, name):
        if name not in self.plugins:
            raise ValueError(f"unknown tool: {name or '(empty)'}")
        return self.plugins[name]

    def __iter__(self):
        return iter(self.plugins.values())
