"""Tools the model can call.

Saturday ships no tools of its own: a project adds them by dropping `.py` files with Plugin subclasses into its
`plugins/` folder (or any folder listed in `[plugins] dirs`). An application with its own tool system supplies a
registry factory instead: `[plugins] registry = "mypackage.tools:ToolRegistry"`, any callable(config) returning an
object with describe(), get(name) and iteration over plugin instances.
"""
import importlib
import importlib.util
import json
import os
import sys


class Plugin:
    """A tool the model can call. Subclass it, set the class attributes, implement run(**arguments)."""

    name = ''
    description = ''
    parameters = {}
    required = ()
    confirm = False

    def __init__(self, config):
        self.config = config

    def describe(self):
        return f"- {self.name}({', '.join(self.parameters)}): {self.description}"

    def summary(self, arguments):
        label = self.name.replace('_', ' ')
        return f"{label} {json.dumps(arguments)}" if arguments else label

    def validate(self, arguments):
        if not isinstance(arguments, dict):
            raise ValueError('arguments must be an object')
        arguments = {key: str(value) for key, value in arguments.items() if key in self.parameters}
        missing = [key for key in self.required if not arguments.get(key)]
        if missing:
            raise ValueError(f"missing arguments: {', '.join(missing)}")
        return arguments

    def run(self, **arguments):
        raise NotImplementedError


def plugin_classes(module):
    for obj in vars(module).values():
        if isinstance(obj, type) and issubclass(obj, Plugin) and obj is not Plugin and obj.name \
                and obj.__module__ == module.__name__:
            yield obj


def load_file(path):
    name = f"saturday_project_plugins.{os.path.splitext(os.path.basename(path))[0]}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Registry:
    """Plugin instances from the project's plugin folders."""

    def __init__(self, config):
        self.plugins = {}
        for folder in config.plugin_dirs:
            folder = os.path.join(config.root, folder)
            if not os.path.isdir(folder):
                continue
            for filename in sorted(os.listdir(folder)):
                if filename.endswith('.py') and not filename.startswith('_'):
                    for cls in plugin_classes(load_file(os.path.join(folder, filename))):
                        self.plugins[cls.name] = cls(config)

    def describe(self):
        return '\n'.join(p.describe() for p in self.plugins.values())

    def get(self, name):
        if name not in self.plugins:
            raise ValueError(f"unknown tool: {name or '(empty)'}")
        return self.plugins[name]

    def __iter__(self):
        return iter(self.plugins.values())

    def __len__(self):
        return len(self.plugins)


def registry(config):
    """Build the tool registry named by `[plugins] registry` (default: Registry above)."""
    module_name, _, attribute = config.registry.partition(':')
    try:
        factory = getattr(importlib.import_module(module_name), attribute or 'Registry')
    except (ImportError, AttributeError) as error:
        raise SystemExit(f"cannot load tool registry {config.registry!r}: {error}")
    return factory(config)
