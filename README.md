# Saturday

A small framework for building your own voice assistant on a **small language model** that runs on your own
hardware (or a free Colab GPU). You describe a persona, write a few dozen example conversations, optionally add
tools, and Saturday handles the rest: LoRA fine-tuning, speech in and out, who-is-talking logins, and the model
server / SSH tunnel dance when the GPU lives on Colab.

It grew out of a 2023 hobby assistant called Saturday; that assistant is now the example project in
[examples/saturday](examples/saturday), and its automation lives in [JERN](https://github.com/IshvaraX/JERN),
which is itself built on this framework.

```powershell
pip install "saturday-ai"               # import name and CLI: saturday
saturday init friday --name=Friday      # scaffold a project
cd friday
saturday talk --text                    # type to it; the first run fine-tunes on Colab (~10 min on a T4)
saturday talk                           # voice: microphone in, speech out
```

## What you get

| Piece | Where | Notes |
|---|---|---|
| Project config | `saturday.toml` | name, persona, model, voice, plugins; any key is also a `--flag` |
| Training data | `data/conversations.txt` | plain text; `User:` / `<Name>:` / `Tool:` lines, `---` between conversations |
| Fine-tuning | `saturday.models.transformers` | LoRA (peft) on any Hugging Face chat model; adapter pushed to the Hub |
| Local inference | `backend = "gguf"` | llama.cpp quantized models on a laptop CPU, no training step |
| Voice | `saturday.voice` | faster-whisper in, edge-tts out, silence-based turn taking |
| Users | `saturday adduser` | names, aliases, how to address each person, optional PIN; guests get a safe prompt |
| Tools | `plugins/*.py` | subclass `saturday.plugins.Plugin`; the model calls them with `<tool_call>` JSON |
| Colab | `saturday.colab` | zips project + framework, provisions a T4, runs the model server, tunnels it home |
| Library | `saturday.assistant` | `Assistant` loop with hooks, `Session`, `ToolCall`; build your own UI on it |

Saturday ships **no tools of its own**. The scaffold includes one example (`roll_dice`); real automation belongs
in your project or in an application like JERN.

## A project

```
friday/
  saturday.toml             identity, model, voice, plugins
  data/conversations.txt    how Friday talks (the fine-tune learns from this)
  data/users.json           who Friday recognises (created by `saturday adduser`, gitignored)
  plugins/example.py        a tool; add more files, each with Plugin subclasses
  .env                      HF_REPO / HF_TOKEN and anything your plugins need (gitignored)
```

Every command runs inside a project (the nearest folder upwards holding `saturday.toml`, or `--root=path`):

```powershell
saturday check              # validate config, data and plugins without loading a model
saturday adduser            # register a person (owner / family / friend / guest, title, PIN)
saturday talk               # model on Colab, voice and tools here
saturday talk --local       # model on this machine (pip install "saturday-ai[local]")
saturday talk --text        # keyboard instead of microphone
saturday finetune           # retrain after editing conversations.txt (Colab; --local to do it here)
saturday model --local      # just the model server on 127.0.0.1:8001 (what the Colab VM runs)
saturday --key=value        # override any setting, e.g. --temperature=0.5 --model_name=Qwen/Qwen2.5-1.5B-Instruct
```

### saturday.toml

```toml
[assistant]
name = "Friday"
author = "Jane Doe"
persona = """You are {name}, a personal voice assistant created by {author}, your boss. ..."""
owner_title = "boss"          # how the owner is addressed; others get the title from users.json

[model]
backend = "transformers"      # or "gguf" for llama.cpp on CPU (inference only)
name = "mistralai/Ministral-3-3B-Instruct-2512-BF16"
temperature = 0.3

[colab]
gpu = "T4"
exclude = ["docs"]            # extra folders kept out of the upload

[voice]
whisper_model = "base.en"
voice = "en-IN-PrabhatNeural"

[plugins]
dirs = ["plugins"]
# registry = "myapp.tools:ToolRegistry"   # an application can hand Saturday its own tool registry

[app]                          # free-form: an application's own settings, reachable as config.<key> and --<key>
```

Keys map onto `saturday.config.Config`: `[model] name` is `model_name`, `[voice] voice` is `voice`, and so on.

### Training data

```
Context: You are talking to Jane (owner, your creator). Address them as 'boss'. It is Monday 02 November 2026, 09:12 AM.
User: Roll a die.
Friday: <tool_call>{"name": "roll_dice", "arguments": {"sides": "6"}}</tool_call>
Tool: rolled a 4 on a 6-sided die
Friday: You rolled a four boss.
---
```

The `Context:` line is exactly what Saturday appends to the system prompt at runtime (from `users.json` and the
clock), so the model learns to use it: titles, guest etiquette, the time and date. Only assistant turns contribute
to the loss. Run `saturday check` after editing; it warns about tool calls to tools you do not have.

### Models

- **transformers** (default): base model + LoRA adapter (rank 16 on the language-model projections). The adapter
  is looked up in `out-adapter/`, then on the Hub at `HF_REPO`; it is reused only if `adapter_config.json` names
  the configured base model, otherwise a fresh one is trained (3 epochs, fp16 autocast). Ministral 3 3B needs
  `transformers>=5`; `Qwen/Qwen2.5-1.5B-Instruct` is a lighter choice.
- **gguf**: `llama-cpp-python` with any GGUF repo, e.g. `name = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"`,
  `file = "*q4_k_m.gguf"`. Persona comes from the system prompt; runs on CPU; always local.
- **remote**: `--model_url=http://host:8001` points the assistant at a running `saturday model` server.

### Building an application on it

```python
from saturday.assistant import Assistant, Session
from saturday.config import configure
from saturday.plugins import registry

config = configure(flags, root)              # saturday.toml + --flags; config.<key> for your [app] settings
assistant = Assistant(config, registry(config), log)
reply, pending = assistant.respond(Session(user), "hello")
```

`Assistant` exposes hooks to override: `rewrite()` a tool call before it runs, `run_arguments()` for extra keyword
arguments a plugin needs, `note()` to collect a per-turn timeline, `confirm_question()` / `give_up()` for wording,
`load_chat()` for how the model is obtained. `saturday.colab.ColabRunner.serve(flags, local_argv)` runs the model on
Colab and your own command here against the tunnel. JERN is the worked example.

## Install

```powershell
pip install "saturday-ai"               # voice + Colab flow (model runs on Colab)
pip install "saturday-ai[local]"        # + torch, transformers>=5, peft: run or fine-tune on this machine
pip install "saturday-ai[gguf]"         # + llama-cpp-python
```

Colab needs `colab` (installed with the package) signed in once (`colab auth`), and an `ssh` client for the tunnel
(on Windows: the OpenSSH Client optional feature). Set `HF_REPO` and `HF_TOKEN` (write scope) in `.env` so the
trained adapter survives the VM.

Development: `pip install -e . --no-deps && python -m unittest discover -s tests`.

## Troubleshooting

- *Colab refused to allocate a runtime*: free-tier limits; wait, or `--gpu=''` for a CPU runtime, or `--local`.
- *archive is N MB*: a virtualenv or weights sits in the project; add it to `[colab] exclude`.
- *CERTIFICATE_VERIFY_FAILED* behind a corporate proxy: Saturday injects the OS trust store (truststore) and ships a
  CA bundle to the `colab` CLI; make sure the proxy's CA is in the Windows store.
- *port 8001 already in use*: something else listens there; stop it or pass `--model_port=8002`.
- *the model says "Tool result" to me*: some GGUF chat templates reject the `tool` role; Saturday retries with tool
  results as user turns, which weaker models sometimes echo. Prefer Qwen or Mistral GGUFs.