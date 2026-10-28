"""saturday: build your own voice assistant on a small language model.

A project is a folder with an `saturday.toml` (name, persona, model, voice, plugins), `data/conversations.txt`
(how the assistant talks, used for LoRA fine-tuning) and optional `plugins/*.py` (tools). See `saturday init`.
"""
__version__ = '0.1.0'

__all__ = ['Assistant', 'Config', 'Plugin', 'Registry', 'Session', 'configure', '__version__']


def __getattr__(name):
    # Lazy so `import saturday` stays cheap (the CLI and the Colab VM import it before heavy deps are needed).
    if name in ('Assistant', 'Session'):
        from saturday import assistant
        return getattr(assistant, name)
    if name in ('Config', 'configure'):
        from saturday import config
        return getattr(config, name)
    if name in ('Plugin', 'Registry'):
        from saturday import plugins
        return getattr(plugins, name)
    raise AttributeError(name)
