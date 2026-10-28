# __NAME__

A voice assistant built with [saturday](https://github.com/vivek09thakur/SATURDAY) __VERSION__.

```
saturday.toml             name, persona, model, voice, plugins
data/conversations.txt    how __NAME__ talks; the LoRA fine-tune learns from this
data/users.json           who __NAME__ recognises (saturday adduser); users.example.json shows the shape
plugins/                  your own tools (see plugins/example.py)
.env                      API keys and tokens (see .env.example)
```

```powershell
saturday check            # validate the project
saturday adduser          # register yourself (optional, enables titles and PINs)
saturday talk --text      # keyboard chat; drop --text for voice
saturday talk --local       # run the model on this machine instead of Colab
saturday finetune           # (re)train the adapter after editing data/conversations.txt
```

Run `saturday help` for every command and `saturday talk --key=value` to override any setting from saturday.toml.
