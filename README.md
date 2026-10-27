# Saturday

A personal voice assistant with a small language model behind it. Say something, Saturday answers out loud and, when needed, does things on your computer: opens sites, plays YouTube, checks the weather, sends email, shuts the PC down.

- **Brain**: [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct), fine-tuned on
  `data/conversations.txt` so it talks like Saturday and knows how to call tools.
- **Ears / voice**: `faster-whisper` (offline speech-to-text) and `edge-tts` (text-to-speech).
- **Hands**: plugins in `plugins/`. The model emits `<tool_call>{"name": ..., "arguments": {...}}</tool_call>`, the
  plugin runs on your machine, the result goes back to the model, and it answers.

By default the **model runs on a Colab GPU** and everything else (microphone, speaker, tools) runs locally, talking to
the model over an SSH tunnel. `--local` runs the model on your machine instead.

The original 2023 version (bag-of-words intent classifier + keyword automations) lives on the `master` branch.

## Layout

```
main.py            entry point
common/            constants.py (identity, persona, model id), common.py (Config + CLI flags), utils.py
controls/voice.py  Listener (mic → whisper), Speaker (edge-tts → speakers), TextIO (keyboard)
controls/tui.py    terminal UI: left panel = menu + conversation (always listening), right panel = the lively clock
plugins/           one Plugin subclass per tool; dropped in a module here = auto-discovered
model/             chat.py (load / fine-tune / generate, RemoteChat), assistant.py (tool-call loop),
                   server.py (model HTTP server), colab.py (runs the model on Colab), data.py
data/              conversations.txt (training data), contacts.json (your contacts, gitignored)
```

## Setup

```powershell
git clone git@github.com:vivek09thakur/SATURDAY.git
cd SATURDAY
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # then fill it in (see below)
copy data\contacts.example.json data\contacts.json   # names + emails for send_email
```

`.env` keys (all optional; a tool that needs a missing key just reports an error):

| Key | Used by |
|---|---|
| `HF_REPO`, `HF_TOKEN` | Keeps the fine-tuned model on the Hugging Face Hub so Colab runs skip training. Token needs *write* scope. |
| `OPENWEATHER_API_KEY` | `weather` tool ([free key](https://openweathermap.org/api)) |
| `SMTP_EMAIL`, `SMTP_PASSWORD` | `send_email` tool. For Gmail use an [App Password](https://myaccount.google.com/apppasswords). |

For the Colab default you also need, once:

```powershell
colab sessions        # google-colab-cli is in requirements.txt; first call opens the Google sign-in
```

and the OpenSSH client (`ssh`), built into Windows 10+ / macOS / Linux.

## Commands

### Talk to Saturday

```powershell
python main.py                 # model on Colab GPU, voice + tools here (default)
python main.py --text          # same, but type instead of speaking
python main.py --tui           # same, in the terminal UI with the clock character; add --text for keyboard only
python main.py --local         # model on this machine (needs a GPU or patience)
python main.py --local --text  # everything local, keyboard only
```

Say **bye** (or Ctrl+C) to stop. Tools that change something (`shutdown`, `send_email`) ask first; answer *yes* / *no*.

The terminal UI (`--tui`, built with [Textual](https://textual.textualize.io/)) is two columns: on the left a panel that shows what Saturday can do, the live
status and the conversation; on the right Saturday as a little rubber-hose clock, drawn with half-block pixels so the
dial is a true circle. It drifts around, blinks, glances, taps a foot, hops, waves while listening, scratches its head
while thinking and flaps its mouth while talking. Replies are typed out character by character. The mic
is always on; **Ctrl+T** opens a chat bar for typing (Esc closes it), **Ctrl+C** or *bye* exits.

What `python main.py` does, step by step:

1. Zips the repo (without `.env`, `contacts.json`, weights) and uploads it to a fresh Colab T4 session.
2. On the VM starts `main.py model`. The model is loaded from the first of: local `out-saturday/` → `HF_REPO` on the
   Hub → base Qwen2.5. A saved fine-tune is only reused if it was built on the same architecture as the configured
   base model (so changing `--model_name` family retrains automatically). If it had to fall back to the base model it
   **fine-tunes right there**, saves, and pushes to
   `HF_REPO` if set (~10–15 min on a T4 the first time; later runs skip this).
3. Opens `ssh -L 8001` to the VM and runs `main.py talk --model_url=http://127.0.0.1:8001` locally.
4. On exit closes the tunnel and stops the VM.

### Fine-tune

```powershell
python main.py finetune                    # on Colab; result pushed to HF_REPO, or downloaded to out-saturday/ if unset
python main.py finetune --local            # on this machine
python main.py finetune --train            # force a retrain even if a trained model exists
python main.py finetune --epochs=5 --learning_rate=5e-5 --train_layers=0   # all layers, more epochs
```

Training data is `data/conversations.txt`: `User:` / `Saturday:` / `Tool:` lines, conversations separated by `---`.
Edit it, run `finetune`, done. Keep tool examples in the exact `<tool_call>` JSON shape the plugins expect.

### Model server only

```powershell
python main.py model --local               # serve POST /generate on 127.0.0.1:8001 (this is what the VM runs)
python main.py talk --model_url=http://127.0.0.1:8001   # point a local Saturday at any model server
```

### Colab options

```powershell
python main.py --gpu=L4                    # T4 (default), L4, A100, or --gpu='' for a CPU runtime
python main.py --keep                      # leave the VM running after exit
python main.py --reuse                     # attach to the existing 'saturday' session instead of creating one
python main.py --session=other-name
colab stop -s saturday                     # stop a kept session by hand
```

### Useful overrides

Any field of `Config` in `common/common.py` can be set with `--name=value`:

```powershell
--model_name=Qwen/Qwen2.5-0.5B-Instruct             # smaller/faster model (weaker at tool calls)
--whisper_model=small.en                            # tiny.en / base.en (default) / small.en / medium.en
--voice=en-US-GuyNeural                             # any edge-tts voice (default en-IN-PrabhatNeural)
--temperature=0                                     # greedy decoding
--max_history=10                                    # user turns kept in context
--silence_seconds=2 --listen_timeout=15             # mic: pause that ends an utterance / how long to wait for speech
```

## Tools

| Tool | What it does | Asks first |
|---|---|---|
| `open_website(site)` | Opens a known site (`gmail`, `github`, `youtube`, `whatsapp`, …) or a URL | |
| `search_web(query)` | Google search in the browser | |
| `play_youtube(query)` | Plays the first matching video | |
| `search_location(place)` | Google Maps | |
| `weather(city)` | Current weather via OpenWeather | |
| `current_time()` | Date and time | |
| `system_info()` | OS, computer and user name | |
| `connected_devices()` | Devices on the LAN (`arp -a`) | |
| `close_tab()` | Ctrl+W in the browser | |
| `send_email(contact, subject, body)` | SMTP to a contact from `data/contacts.json` | yes |
| `shutdown()` | Shuts the computer down | yes |

Adding one: create a `Plugin` subclass in any module under `plugins/` with `name`, `description`, `parameters`,
`required`, optional `confirm = True`, and a `run(**arguments)` returning a string. Then add a couple of examples to
`data/conversations.txt` and fine-tune.

## Troubleshooting

- **`the 'colab' CLI is not installed`** – `pip install google-colab-cli`, or use `--local`.
- **`could not allocate a runtime`** – Colab quota/capacity; wait, try `--gpu=''`, or `--local`.
- **`CERTIFICATE_VERIFY_FAILED` from the colab CLI** – you are behind a TLS-inspecting proxy; Saturday exports the OS
  certificate store to `export/ca-bundle.pem` automatically. Set `REQUESTS_CA_BUNDLE` yourself to override.
- **`push to <repo> failed`** – `HF_TOKEN` missing or read-only. The model is still saved on the VM for this session.
- **Nothing is heard** – lower `--silence_threshold` (default `0.01`) or check the default input device.
- **Speech fails / silent** – `edge-tts` needs internet; the reply is still printed.
