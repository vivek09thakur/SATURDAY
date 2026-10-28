import asyncio
import io


class Listener:
    """Microphone → faster-whisper. Recording starts on speech and stops after a pause."""

    CHUNK_SECONDS = 0.1

    def __init__(self, config, log=print, on_state=None):
        import numpy as np
        import sounddevice as sd
        from faster_whisper import WhisperModel
        self.np, self.sd = np, sd
        self.config = config
        self.log = log
        self.on_state = on_state or (lambda state: None)
        cuda = config.device.startswith('cuda')
        self.model = WhisperModel(config.whisper_model, device='cuda' if cuda else 'cpu',
                                  compute_type='float16' if cuda else 'int8')

    def record(self, cancel=None):
        np = self.np
        cfg = self.config
        chunk = int(cfg.sample_rate * self.CHUNK_SECONDS)
        frames, speaking, silent, waited = [], False, 0.0, 0.0
        self.on_state('listening')
        with self.sd.InputStream(samplerate=cfg.sample_rate, channels=1, dtype='float32', blocksize=chunk) as stream:
            while True:
                if cancel is not None and cancel():
                    return None
                data, _ = stream.read(chunk)
                data = data[:, 0]
                loud = float(np.sqrt(np.mean(data ** 2))) > cfg.silence_threshold
                if not speaking:
                    waited += self.CHUNK_SECONDS
                    if loud:
                        speaking = True
                    elif waited >= cfg.listen_timeout:
                        return None
                    frames = frames[-5:]
                else:
                    silent = 0.0 if loud else silent + self.CHUNK_SECONDS
                    if silent >= cfg.silence_seconds or len(frames) * self.CHUNK_SECONDS >= cfg.max_record_seconds:
                        break
                frames.append(data)
        return np.concatenate(frames)

    def listen(self, cancel=None):
        audio = self.record(cancel)
        if audio is None:
            self.on_state('idle')
            return ''
        self.on_state('thinking')
        segments, _ = self.model.transcribe(audio, language='en', beam_size=1, vad_filter=True)
        kept = [s.text.strip() for s in segments if s.no_speech_prob < 0.6 and s.avg_logprob > -1.0]
        text = ' '.join(kept).strip()
        if text:
            self.log('you', text)
        return text


class Speaker:
    """Text → edge-tts (mp3 bytes) → speakers. Falls back to printing if synthesis fails (e.g. offline)."""

    def __init__(self, config, log=print, on_state=None):
        import sounddevice as sd
        import soundfile as sf
        self.sd, self.sf = sd, sf
        self.config = config
        self.log = log
        self.on_state = on_state or (lambda state: None)

    async def synthesize(self, text):
        import edge_tts
        audio = bytearray()
        async for chunk in edge_tts.Communicate(text, self.config.voice).stream():
            if chunk['type'] == 'audio':
                audio.extend(chunk['data'])
        return bytes(audio)

    def speak(self, text):
        self.log('speech', text)
        try:
            data, rate = self.sf.read(io.BytesIO(asyncio.run(self.synthesize(text))), dtype='float32')
            self.on_state('speaking')
            self.sd.play(data, rate)
            self.sd.wait()
        except Exception as error:
            self.log('error', f"speech failed: {type(error).__name__}: {error}")
        finally:
            self.on_state('idle')


class VoiceIO:

    def __init__(self, config, log=print, on_state=None):
        self.speaker = Speaker(config, log, on_state)
        self.listener = Listener(config, log, on_state)

    def listen(self, cancel=None):
        return self.listener.listen(cancel)

    def say(self, text):
        self.speaker.speak(text)


class TextIO:

    CPS = 45

    def __init__(self, config):
        self.config = config

    def listen(self, cancel=None):
        try:
            return input('You: ').strip()
        except (EOFError, KeyboardInterrupt):
            return 'bye'

    def say(self, text):
        import sys
        import time
        sys.stdout.write(f'{self.config.name}: ')
        for ch in text:
            sys.stdout.write(ch)
            sys.stdout.flush()
            time.sleep(1 / self.CPS)
        sys.stdout.write('\n\n')
        sys.stdout.flush()
