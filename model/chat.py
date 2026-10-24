import os
import time
from contextlib import nullcontext

from common.utils import timed, trim_loop, wait_for_health


class ChatBackend:

    def __init__(self, config, log=print):
        self.config = config
        self.log = log
        self.source = None

    def load(self, system_prompt=''):
        return self

    def generate(self, messages):
        raise NotImplementedError


class SaturdayChat(ChatBackend):
    """SmolLM2 wrapper. Picks the first available of: local out_dir, Hugging Face Hub repo, base model.
    Loading the base model triggers a fine-tune, which is saved locally and pushed to the Hub when configured."""

    def __init__(self, config, log=print):
        super().__init__(config, log)
        self.tokenizer = None
        self.model = None

    def is_trained(self):
        return os.path.exists(os.path.join(self.config.out_dir, 'config.json'))

    def on_hub(self):
        repo = self.config.hf_repo
        if not repo:
            return False
        try:
            from huggingface_hub import HfApi
            return HfApi().file_exists(repo, 'config.json')
        except Exception as error:
            self.log('error', f"could not reach the Hub for {repo}: {type(error).__name__}: {error}")
            return False

    def resolve_source(self):
        cfg = self.config
        if cfg.train:
            return cfg.model_name
        if self.is_trained():
            return cfg.out_dir
        if self.on_hub():
            return cfg.hf_repo
        return cfg.model_name

    def load(self, system_prompt=''):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        cfg = self.config
        torch.manual_seed(cfg.seed)
        self.source = self.resolve_source()
        self.log('model', f"loading {self.source} on {cfg.device}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.source)
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(self.source).float().to(cfg.device)
        if self.source == cfg.model_name:
            self.finetune(system_prompt)
        self.model.eval()
        return self

    def trainable_parameters(self):
        layers = self.config.train_layers
        if layers <= 0:
            return list(self.model.parameters())
        self.model.requires_grad_(False)
        modules = list(self.model.model.layers[-layers:]) + [self.model.model.norm]
        for module in modules:
            module.requires_grad_(True)
        return [p for module in modules for p in module.parameters()]

    def finetune(self, system_prompt):
        import torch
        from torch.utils.data import DataLoader
        from model.data import ConversationDataset, ConversationFile
        cfg = self.config
        conversations = ConversationFile(cfg.data_path, system_prompt).load()
        dataset = ConversationDataset(conversations, self.tokenizer, cfg.max_length)
        loader = DataLoader(dataset, batch_size=cfg.batch_size, shuffle=True, collate_fn=dataset.collate)
        params = self.trainable_parameters()
        optimizer = torch.optim.AdamW(params, lr=cfg.learning_rate)
        cuda = cfg.device.startswith('cuda')
        scaler = torch.amp.GradScaler('cuda', enabled=cuda)
        autocast = torch.autocast('cuda', dtype=torch.float16) if cuda else nullcontext()
        # Non-reentrant checkpointing works with frozen embeddings.
        self.model.config.use_cache = False
        self.model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        self.log('model', f"fine-tuning on {len(dataset)} conversations for {cfg.epochs} epochs, "
                          f"{sum(p.numel() for p in params) / 1e6:.0f}M trainable parameters")
        self.model.train()
        step = 0
        for epoch in range(cfg.epochs):
            started = time.time()
            for i, batch in enumerate(loader, 1):
                batch = {k: v.to(cfg.device) for k, v in batch.items()}
                with autocast:
                    loss = self.model(**batch).loss / cfg.accumulation
                scaler.scale(loss).backward()
                if i % cfg.accumulation == 0 or i == len(loader):
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(params, 1.0)
                    scaler.step(optimizer)
                    scaler.update()
                    optimizer.zero_grad(set_to_none=True)
                    step += 1
                    self.log('model', f"epoch {epoch + 1}/{cfg.epochs} step {step}: "
                                      f"loss {loss.item() * cfg.accumulation:.4f} ({time.time() - started:.0f}s)")
                    started = time.time()
        self.model.gradient_checkpointing_disable()
        self.model.config.use_cache = True
        self.model.eval()
        self.model.requires_grad_(False)
        # fp16 on disk halves the size; load() upcasts to fp32 again.
        self.model.half().save_pretrained(cfg.out_dir)
        self.tokenizer.save_pretrained(cfg.out_dir)
        self.log('model', f"saved fine-tuned model to {cfg.out_dir}")
        if cfg.hf_repo:
            self.push()
        self.model.float()
        self.source = cfg.out_dir

    def push(self):
        repo = self.config.hf_repo
        self.log('model', f"pushing fine-tuned model to {repo}")
        try:
            self.model.push_to_hub(repo, private=True)
            self.tokenizer.push_to_hub(repo, private=True)
            self.log('model', f"pushed to https://huggingface.co/{repo}")
        except Exception as error:
            self.log('error', f"push to {repo} failed (is HF_TOKEN set with write access?): {type(error).__name__}: {error}")

    def generation_kwargs(self):
        cfg = self.config
        kwargs = dict(max_new_tokens=cfg.max_new_tokens, pad_token_id=self.tokenizer.pad_token_id,
                      repetition_penalty=cfg.repetition_penalty, no_repeat_ngram_size=cfg.no_repeat_ngram_size)
        if cfg.temperature > 0:
            kwargs.update(do_sample=True, temperature=cfg.temperature, top_p=0.9)
        else:
            kwargs.update(do_sample=False)
        return kwargs

    def generate(self, messages):
        import torch
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors='pt', add_special_tokens=False).to(self.config.device)
        with torch.no_grad():
            output = timed(self.log, f"generated ({inputs['input_ids'].shape[1]} prompt tokens)",
                           lambda: self.model.generate(**inputs, **self.generation_kwargs()))
        new_tokens = output[0, inputs['input_ids'].shape[1]:]
        return trim_loop(self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip())


class RemoteChat(ChatBackend):
    """Forwards generation to a model server (model/server.py), e.g. one running on a Colab GPU."""

    TIMEOUT = 600

    def __init__(self, config, log=print):
        super().__init__(config, log)
        self.source = config.model_url.rstrip('/')

    def load(self, system_prompt=''):
        self.log('model', f"waiting for model server at {self.source}")
        if not wait_for_health(self.source):
            raise SystemExit(f"no model server at {self.source}")
        return self

    def generate(self, messages):
        import requests
        response = timed(self.log, f"generated remotely ({len(messages)} messages)", lambda: requests.post(
            f'{self.source}/generate', json={'messages': messages}, timeout=self.TIMEOUT))
        response.raise_for_status()
        return response.json()['text']


def chat_backend(config, log=print):
    return RemoteChat(config, log) if config.model_url else SaturdayChat(config, log)
