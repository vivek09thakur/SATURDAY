# Saturday (example project)

The assistant the Saturday framework was extracted from: a 2023 hobby voice assistant rebuilt on a small language
model. It is a plain Saturday project, so it doubles as the reference example.

- Persona and settings: [saturday.toml](saturday.toml)
- 39 training conversations: [data/conversations.txt](data/conversations.txt) (owner, family and guest contexts;
  greetings, small talk, time and date from context, polite refusals)
- Its automation (websites, YouTube, weather, mail, shutdown, Wi-Fi scan) moved to
  [JERN](https://github.com/IshvaraX/JERN), which is built on Saturday too.
- Trained LoRA adapter for Ministral 3 3B on the Hub: `vivek09thakur/saturday` (private; set `HF_REPO`/`HF_TOKEN`
  in `.env` to reuse yours)

```powershell
cd examples/saturday
saturday check
saturday talk              # voice, model on Colab; --text for keyboard, --local for this machine
```
