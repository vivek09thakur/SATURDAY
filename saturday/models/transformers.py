"""Hugging Face transformers backend: any chat model from the Hub, with a LoRA adapter trained on the project's data."""
import os
import time
from contextlib import nullcontext

from saturday.models import ChatBackend
from saturday.utils import timed, trim_loop

ADAPTER_FILE = 'adapter_config.json'
LORA_TARGETS = ('q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj')
STALE_HUB_FILES = ('model.safetensors', 'config.json', 'generation_config.json')


class TransformersChat(ChatBackend):
    """Base model + LoRA adapter. The adapter is looked up in out_dir, then on the Hub (HF_REPO); it is only reused if
    it was trained on the configured base model. Without one, load() fine-tunes a fresh adapter, saves it, pushes it
    to the Hub when configured, and merges it into the base weights for inference."""

    def __init__(self, config, log=print):
        super().__init__(config, log)
        self.tokenizer = None
        self.model = None


    def adapter_base(self, source):
        """Base model an adapter at `source` (local dir or Hub repo) was trained on, or None if there is none."""
        import json
        try:
            if os.path.isdir(source):
                path = os.path.join(source, ADAPTER_FILE)
                if not os.path.exists(path):
                    return None
            else:
                from huggingface_hub import HfApi, hf_hub_download
                if not HfApi().file_exists(source, ADAPTER_FILE):
                    return None
                path = hf_hub_download(source, ADAPTER_FILE)
            with open(path, encoding='utf-8') as f:
                return json.load(f).get('base_model_name_or_path')
        except Exception as error:
            self.log('error', f"could not inspect {source}: {type(error).__name__}: {error}")
            return None

    def resolve_adapter(self):
        cfg = self.config
        if cfg.train:
            return None
        for source in (cfg.path(cfg.out_dir), cfg.hf_repo):
            if not source:
                continue
            base = self.adapter_base(source)
            if base == cfg.model_name:
                return source
            if base is not None:
                self.log('info', f"adapter at {source} was trained on {base}, not {cfg.model_name}; training again")
        return None


    def tokenizer_kwargs(self):
        return {'fix_mistral_regex': True} if 'mistral' in self.config.model_name.lower() else {}

    def load_base(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        cfg = self.config
        cuda = cfg.device.startswith('cuda')
        dtype = torch.float16 if cuda else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(cfg.model_name, **self.tokenizer_kwargs())
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        try:
            model = AutoModelForCausalLM.from_pretrained(cfg.model_name, dtype=dtype)
        except ValueError:
            from transformers import AutoModelForImageTextToText
            model = AutoModelForImageTextToText.from_pretrained(cfg.model_name, dtype=dtype)
        self.model = model.to(cfg.device)

    def load(self, system_prompt=''):
        import torch
        cfg = self.config
        torch.manual_seed(cfg.seed)
        adapter = self.resolve_adapter()
        self.log('model', f"loading {cfg.model_name} on {cfg.device}" + (f" with adapter {adapter}" if adapter else ''))
        self.load_base()
        if adapter is None:
            self.finetune(system_prompt)
        else:
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, adapter).merge_and_unload()
            self.source = adapter
        self.model.eval()
        return self


    def lora_targets(self):
        import torch
        names = []
        for name, module in self.model.named_modules():
            if isinstance(module, torch.nn.Linear) and name.split('.')[-1] in LORA_TARGETS \
                    and 'vision' not in name and 'multi_modal' not in name:
                names.append(name)
        return names

    def set_cache(self, enabled):
        for config in (self.model.config, getattr(self.model.config, 'text_config', None)):
            if config is not None:
                config.use_cache = enabled

    def finetune(self, system_prompt):
        import torch
        from peft import LoraConfig, get_peft_model
        from torch.utils.data import DataLoader
        from saturday.models.data import ConversationDataset, ConversationFile
        cfg = self.config
        conversations = ConversationFile(cfg.path(cfg.data_path), system_prompt, cfg.name).load()
        dataset = ConversationDataset(conversations, self.tokenizer, cfg.max_length)
        loader = DataLoader(dataset, batch_size=cfg.batch_size, shuffle=True, collate_fn=dataset.collate)
        cuda = cfg.device.startswith('cuda')
        self.set_cache(False)
        self.model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        self.model.enable_input_require_grads()
        lora = LoraConfig(r=cfg.lora_rank, lora_alpha=cfg.lora_alpha, lora_dropout=cfg.lora_dropout,
                          target_modules=self.lora_targets(), task_type='CAUSAL_LM')
        peft_model = get_peft_model(self.model, lora)
        params = [p for p in peft_model.parameters() if p.requires_grad]
        optimizer = torch.optim.AdamW(params, lr=cfg.learning_rate)
        scaler = torch.amp.GradScaler('cuda', enabled=cuda)
        autocast = torch.autocast('cuda', dtype=torch.float16) if cuda else nullcontext()
        self.log('model', f"fine-tuning LoRA (r={cfg.lora_rank}) on {len(dataset)} conversations for {cfg.epochs} epochs, "
                          f"{sum(p.numel() for p in params) / 1e6:.1f}M trainable parameters")
        peft_model.train()
        step = 0
        for epoch in range(cfg.epochs):
            started = time.time()
            for i, batch in enumerate(loader, 1):
                batch = {k: v.to(cfg.device) for k, v in batch.items()}
                with autocast:
                    loss = peft_model(**batch).loss / cfg.accumulation
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
        peft_model.eval()
        self.model.gradient_checkpointing_disable()
        self.set_cache(True)
        peft_model.save_pretrained(cfg.path(cfg.out_dir))
        self.tokenizer.save_pretrained(cfg.path(cfg.out_dir))
        self.log('model', f"saved adapter to {cfg.out_dir}")
        if cfg.hf_repo:
            self.push(peft_model)
        self.model = peft_model.merge_and_unload()
        self.model.requires_grad_(False)
        self.source = cfg.out_dir

    def push(self, peft_model):
        repo = self.config.hf_repo
        self.log('model', f"pushing adapter to {repo}")
        try:
            peft_model.push_to_hub(repo, private=True)
            self.tokenizer.push_to_hub(repo, private=True)
            from huggingface_hub import HfApi
            api = HfApi()
            for name in STALE_HUB_FILES:
                if api.file_exists(repo, name):
                    api.delete_file(name, repo, commit_message=f'remove stale {name}')
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
