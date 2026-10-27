import torch
from torch.utils.data import Dataset

from common.constants import IGNORE_INDEX, SEPARATOR, SPEAKERS


class ConversationFile:
    """Plain-text chats: `User: ...` / `Saturday: ...` / `Tool: ...` lines, conversations separated by `---`.
    An optional leading `Context: ...` line (who is talking, the time) is appended to the system prompt."""

    def __init__(self, path, system_prompt):
        self.path = path
        self.system_prompt = system_prompt

    def load(self):
        conversations, current = [], []
        with open(self.path, encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                if line.strip() == SEPARATOR:
                    if current:
                        conversations.append(current)
                        current = []
                    continue
                speaker, sep, content = line.partition(': ')
                if sep and speaker in SPEAKERS:
                    current.append({'role': SPEAKERS[speaker], 'content': content})
                elif current:
                    current[-1]['content'] += '\n' + line
                elif line.strip():
                    raise ValueError(f"line without a speaker: {line}")
        if current:
            conversations.append(current)
        for conversation in conversations:
            for message in conversation:
                message['content'] = message['content'].strip()
        result = []
        for conversation in conversations:
            system = self.system_prompt
            if conversation and conversation[0]['role'] == 'system':
                system = f"{system}\n{conversation[0]['content']}"
                conversation = conversation[1:]
            result.append([{'role': 'system', 'content': system}] + conversation)
        return result


class ConversationDataset(Dataset):
    """Tokenizes with the model's chat template; only assistant tokens contribute to the loss."""

    def __init__(self, conversations, tokenizer, max_length):
        self.tokenizer = tokenizer
        self.examples = [self.encode(c, max_length) for c in conversations]

    def render(self, messages):
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return self.tokenizer(text, add_special_tokens=False)['input_ids']

    def encode(self, messages, max_length):
        input_ids, labels, previous = [], [], 0
        for i, message in enumerate(messages):
            ids = self.render(messages[:i + 1])
            delta = ids[previous:]
            previous = len(ids)
            input_ids.extend(delta)
            labels.extend(delta if message['role'] == 'assistant' else [IGNORE_INDEX] * len(delta))
        return {'input_ids': input_ids[:max_length], 'labels': labels[:max_length]}

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, index):
        return self.examples[index]

    def collate(self, batch):
        length = max(len(item['input_ids']) for item in batch)
        pad = self.tokenizer.pad_token_id
        rows = [(item['input_ids'], item['labels'], length - len(item['input_ids'])) for item in batch]
        return {
            'input_ids': torch.tensor([ids + [pad] * n for ids, _, n in rows]),
            'attention_mask': torch.tensor([[1] * len(ids) + [0] * n for ids, _, n in rows]),
            'labels': torch.tensor([labels + [IGNORE_INDEX] * n for _, labels, n in rows]),
        }
