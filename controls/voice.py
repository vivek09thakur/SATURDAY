import asyncio
import io

import numpy as np


class Listener:
    """Microphone → faster-whisper. Recording starts on speech and stops after a pause."""

    CHUNK_SECONDS = 0.1

    def __init__(self, config, log=print):
        import sounddevice as sd
        from faster_whisper import WhisperModel
        self.sd = sd
        self.config = config
        self.log = log
        cuda = config.device.startswith('cuda')
        self.model = WhisperModel(config.whisper_model, device='cuda' if cuda else 'cpu',
                                  compute_type='float16' if cuda else 'int8')

    def record(self):
        cfg = self.config
        chunk = int(cfg.sample_rate * self.CHUNK_SECONDS)
        frames, speaking, silent, waited = [], False, 0.0, 0.0
        print('Listening...', flush=True)
        with self.sd.InputStream(samplerate=cfg.sample_rate, channels=1, dtype='float32', blocksize=chunk) as stream:
            while True:
                data, _ = stream.read(chunk)
                data = data[:, 0]
                loud = float(np.sqrt(np.mean(data ** 2))) > cfg.silence_threshold
                if not speaking:
                    waited += self.CHUNK_SECONDS
                    if loud:
                        speaking = True
                    elif waited >= cfg.listen_timeout:
                        return None
                    frames = frames[-5:]  # keep a little lead-in so the first word is not clipped
                else:
                    silent = 0.0 if loud else silent + self.CHUNK_SECONDS
                    if silent >= cfg.silence_seconds or len(frames) * self.CHUNK_SECONDS >= cfg.max_record_seconds:
                        break
                frames.append(data)
        return np.concatenate(frames)

    def listen(self):
        audio = self.record()
        if audio is None:
            return ''
        segments, _ = self.model.transcribe(audio, language='en', beam_size=1, vad_filter=True)
        text = ' '.join(segment.text.strip() for segment in segments).strip()
        if text:
            print(f"You: {text}", flush=True)
        return text


class Speaker:
    """Text → edge-tts (mp3 bytes) → speakers. Falls back to printing if synthesis fails (e.g. offline)."""

    def __init__(self, config, log=print):
        import sounddevice as sd
        import soundfile as sf
        self.sd, self.sf = sd, sf
        self.config = config
        self.log = log

    async def synthesize(self, text):
        import edge_tts
        audio = bytearray()
        async for chunk in edge_tts.Communicate(text, self.config.voice).stream():
            if chunk['type'] == 'audio':
                audio.extend(chunk['data'])
        return bytes(audio)

    def speak(self, text):
        print(f"Saturday: {text}", flush=True)
        try:
            data, rate = self.sf.read(io.BytesIO(asyncio.run(self.synthesize(text))), dtype='float32')
            self.sd.play(data, rate)
            self.sd.wait()
        except Exception as error:
            self.log('error', f"speech failed: {type(error).__name__}: {error}")


class VoiceIO:

    def __init__(self, config, log=print):
        self.speaker = Speaker(config, log)
        self.listener = Listener(config, log)

    def listen(self):
        return self.listener.listen()

    def say(self, text):
        self.speaker.speak(text)


class TextIO:

    def listen(self):
        try:
            return input('You: ').strip()
        except (EOFError, KeyboardInterrupt):
            return 'bye'

    def say(self, text):
        print(f"Saturday: {text}\n", flush=True)
