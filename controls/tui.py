"""Terminal UI built with Textual.

 ┌──────────────────────────────────────┬──────────────────┐
 │ Saturday - listening                 │                  │
 │ can: weather | youtube | email | ... │   the clock      │
 │                                      │   (drawn as      │
 │ You: ...                             │    half-block    │
 │ Saturday: ...                        │    pixels, so    │
 │                                      │    it is round)  │
 ├──────────────────────────────────────┤                  │
 │ > typed text   (Ctrl+T toggles)      │                  │
 └──────────────────────────────────────┴──────────────────┘

The microphone is always on (voice mode). Ctrl+T opens a chat bar for typing; Ctrl+C quits.
"""
import math
import queue
import random
import threading
import time

from rich.segment import Segment
from rich.style import Style
from textual.app import App
from textual.binding import Binding
from textual.containers import Vertical
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Input, RichLog, Static

from common.constants import NAME
from common.utils import greeting, is_yes
from model.assistant import Session

ORANGE, DARK, CREAM, INK, AMBER, DIM = '#f08a1d', '#8a4a08', '#fff3dc', '#2b231c', '#ffb347', '#c98a4a'
STATUS = {'idle': 'ready', 'listening': 'listening', 'thinking': 'thinking', 'speaking': 'talking'}


# --- pixel painter: each terminal cell is two vertically stacked pixels, so pixels are square ---------

class Painter:

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.px = [[None] * width for _ in range(height)]

    def dot(self, x, y, color):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = color

    def disc(self, cx, cy, r, color, ry=None):
        ry = r if ry is None else ry
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if ((x - cx) / r) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.dot(x, y, color)

    def ring(self, cx, cy, r, color, thickness=1.0, start=0.0, end=360.0):
        # start/end in degrees, 0 = right, 90 = down (screen coordinates)
        steps = max(24, int(r * 12))
        for i in range(steps + 1):
            a = math.radians(start + (end - start) * i / steps)
            self.disc(cx + r * math.cos(a), cy + r * math.sin(a), thickness / 2, color)

    def line(self, x0, y0, x1, y1, color, thickness=1.0):
        steps = max(1, int(math.hypot(x1 - x0, y1 - y0) * 2))
        for i in range(steps + 1):
            t = i / steps
            self.disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, thickness / 2, color)

    def strip(self, row):
        top, bottom = self.px[2 * row], self.px[2 * row + 1] if 2 * row + 1 < self.h else [None] * self.w
        segments = []
        for t, b in zip(top, bottom):
            if t is None and b is None:
                segments.append(Segment(' '))
            elif t == b:
                segments.append(Segment('█', Style(color=t)))
            elif b is None:
                segments.append(Segment('▀', Style(color=t)))
            elif t is None:
                segments.append(Segment('▄', Style(color=b)))
            else:
                segments.append(Segment('▀', Style(color=t, bgcolor=b)))
        return Strip(segments, self.w)


# --- the character --------------------------------------------------------------------------------------

class Pose:
    """Defaults are the reference pose: left finger up, right hand on hip, big open smile."""

    def __init__(self, **kw):
        self.eyes = 'open'    # open | wide | closed | happy
        self.look = 0         # -1 left, 0 centre, 1 right
        self.mouth = 'smile'  # smile | talk | hmm | whistle | flat
        self.talk = 0.0       # 0..1 mouth opening while talking
        self.arm_l = 'point'  # point | wave | hip | down
        self.arm_r = 'hip'    # hip | scratch | down | out
        self.legs = 'stand'   # stand | tap_l | tap_r | hop
        self.ripples = 0      # 0..3 sound ripples next to the head while listening
        self.question = False
        for k, v in kw.items():
            setattr(self, k, v)


class Animator:
    """Idle is a stream of small random gestures; the other states are fixed poses with motion."""

    GESTURES = [  # (weight, duration, overrides)
        (6, 0.15, dict(eyes='closed')),
        (3, 1.2, dict(look=-1)), (3, 1.2, dict(look=1)),
        (2, 1.5, dict(legs='tap_l')), (2, 1.5, dict(legs='tap_r')),
        (2, 1.0, dict(arm_l='wave')), (1, 1.2, dict(arm_r='out', look=1)),
        (2, 0.8, dict(legs='hop', eyes='happy')),
        (1, 2.0, dict(eyes='closed', mouth='whistle', arm_l='hip')),
        (1, 1.5, dict(eyes='happy', arm_l='hip')),
        (1, 1.0, dict(arm_l='down', arm_r='down', mouth='flat')),
        (5, 1.0, dict()),
    ]

    def __init__(self):
        self.gesture, self.until = {}, 0.0

    def pick(self, now):
        r = random.uniform(0, sum(w for w, _, _ in self.GESTURES))
        for w, dur, pose in self.GESTURES:
            r -= w
            if r <= 0:
                self.gesture, self.until = pose, now + dur
                return

    def pose(self, state, now):
        if state in ('idle', 'listening'):
            if now >= self.until:
                self.pick(now)
                if state == 'listening' and self.gesture.get('eyes') == 'closed':
                    self.gesture = {}
            pose = Pose(**self.gesture)
            if state == 'listening':
                pose.ripples = 1 + int(now * 4) % 3
                if pose.eyes == 'open':
                    pose.eyes = 'wide'
                if pose.arm_l == 'point' and int(now) % 3 == 0:
                    pose.arm_l = 'wave'
            return pose
        if state == 'thinking':
            return Pose(look=1, mouth='hmm', arm_l='hip', arm_r='scratch', question=int(now * 2) % 2 == 0)
        if state == 'speaking':
            return Pose(mouth='talk', talk=0.5 + 0.5 * math.sin(now * 22), arm_l='wave' if int(now * 1.5) % 2 else 'point')
        return Pose()


def draw_character(p, cx, cy, R, pose, now):
    """Draw Saturday centred at (cx, cy) with face radius R (all in pixels)."""
    hop = 0.2 * R if pose.legs == 'hop' else 0
    cy -= hop
    white = '#ffffff'

    def glove(x, y, finger=None):
        p.disc(x, y, 0.19 * R, white)
        p.ring(x, y, 0.19 * R, INK, 0.9)
        if finger is not None:
            fx, fy = x + finger[0] * R, y + finger[1] * R
            p.line(x, y, fx, fy, white, 0.13 * R)
            p.line(x, y, fx, fy, INK, 0.13 * R + 1.6)
            p.line(x, y, fx, fy, white, 0.13 * R)
            p.disc(x, y, 0.19 * R - 0.6, white)

    def arm(shoulder, elbow, hand, cuff=False):
        for a, b in ((shoulder, elbow), (elbow, hand)):
            p.line(*a, *b, INK, 0.13 * R + 1.6)
        for a, b in ((shoulder, elbow), (elbow, hand)):
            p.line(*a, *b, ORANGE, 0.13 * R)
        if cuff:  # striped wristband
            ex, ey = elbow
            hx, hy = hand
            for t in (0.6, 0.78):
                x, y = ex + (hx - ex) * t, ey + (hy - ey) * t
                p.disc(x, y, 0.1 * R, INK)
                p.disc(x, y, 0.065 * R, ORANGE)

    # legs: thin dark sticks, orange shoes turned outward
    for side in (-1, 1):
        lift = 0.18 * R if (pose.legs == 'tap_l' and side < 0) or (pose.legs == 'tap_r' and side > 0) else 0
        tuck = 0.25 * R if pose.legs == 'hop' else 0
        top = (cx + side * 0.2 * R, cy + 0.97 * R)
        foot = (cx + side * 0.26 * R, cy + 1.5 * R - lift - tuck + hop)
        p.line(*top, *foot, INK, 1.3)
        sx, sy = foot[0] + side * 0.17 * R, foot[1]
        p.disc(sx, sy, 0.3 * R, INK, ry=0.16 * R)
        p.disc(sx, sy, 0.3 * R - 1.0, ORANGE, ry=0.16 * R - 1.0)
        p.disc(sx - side * 0.08 * R, sy - 0.1 * R, 0.14 * R, INK, ry=0.12 * R)  # ankle
        p.disc(sx - side * 0.08 * R, sy - 0.1 * R, 0.14 * R - 1.0, ORANGE, ry=0.12 * R - 1.0)

    # arms (drawn before the face so the shoulders tuck under it)
    sh_l, sh_r = (cx - 0.88 * R, cy + 0.15 * R), (cx + 0.88 * R, cy + 0.15 * R)
    if pose.arm_l == 'point':
        hand = (cx - 1.32 * R, cy - 0.62 * R)
        arm(sh_l, (cx - 1.42 * R, cy - 0.05 * R), hand, cuff=True)
        glove(*hand, finger=(0.02, -0.3))
    elif pose.arm_l == 'wave':
        hand = (cx - 1.5 * R, cy - 0.9 * R)
        arm(sh_l, (cx - 1.5 * R, cy - 0.2 * R), hand, cuff=True)
        glove(*hand)
    elif pose.arm_l == 'hip':
        hand = (cx - 1.0 * R, cy + 0.62 * R)
        arm(sh_l, (cx - 1.45 * R, cy + 0.4 * R), hand)
        glove(*hand)
    else:
        hand = (cx - 1.2 * R, cy + 0.75 * R)
        arm(sh_l, (cx - 1.15 * R, cy + 0.45 * R), hand)
        glove(*hand)
    if pose.arm_r == 'hip':
        hand = (cx + 1.0 * R, cy + 0.62 * R)
        arm(sh_r, (cx + 1.45 * R, cy + 0.4 * R), hand, cuff=True)
        glove(*hand)
    elif pose.arm_r == 'scratch':
        hand = (cx + 0.95 * R, cy - 1.08 * R)
        arm(sh_r, (cx + 1.5 * R, cy - 0.45 * R), hand, cuff=True)
        glove(*hand)
    elif pose.arm_r == 'out':
        hand = (cx + 1.65 * R, cy - 0.3 * R)
        arm(sh_r, (cx + 1.35 * R, cy + 0.1 * R), hand, cuff=True)
        glove(*hand, finger=(0.28, -0.1))
    else:
        hand = (cx + 1.2 * R, cy + 0.75 * R)
        arm(sh_r, (cx + 1.15 * R, cy + 0.45 * R), hand)
        glove(*hand)

    # face: orange disc with a thick dark rim
    p.disc(cx, cy, R, INK)
    p.disc(cx, cy, R - 1.6, ORANGE)
    for i in range(12):  # tick marks: long bars at 12/3/6/9, short dashes between, inset from the rim
        a = math.radians(i * 30 - 90)
        major = i % 3 == 0
        r0, r1, thick = (0.64, 0.86, 2.0) if major else (0.74, 0.86, 1.3)
        p.line(cx + r0 * R * math.cos(a), cy + r0 * R * math.sin(a), cx + r1 * R * math.cos(a), cy + r1 * R * math.sin(a), INK, thick)
    p.disc(cx, cy + 0.02 * R, 0.07 * R, INK)  # nose

    # eyes: tall almonds with lashes, big pupils sitting low and inward
    rx, ry = 0.17 * R, 0.29 * R
    for side in (-1, 1):
        ex, ey = cx + side * 0.4 * R, cy - 0.12 * R
        if pose.eyes == 'closed':
            p.line(ex - rx, ey + 0.05 * R, ex + rx, ey + 0.05 * R, INK, 1.4)
        elif pose.eyes == 'happy':
            p.ring(ex, ey + 0.12 * R, rx * 1.1, INK, 1.5, start=200, end=340)
        else:
            p.disc(ex, ey, rx + 1.0, INK, ry=ry + 1.0)
            p.disc(ex, ey, rx, white, ry=ry)
            pr = (0.08, 0.14) if pose.eyes == 'wide' else (0.1, 0.17)
            px, py = ex + pose.look * 0.05 * R - side * 0.03 * R, ey + 0.09 * R
            p.disc(px, py, pr[0] * R, INK, ry=pr[1] * R)
            p.dot(px - pr[0] * R * 0.4, py - pr[1] * R * 0.5, white)
        for k in (-1, 0, 1):  # three lashes on the outer upper rim
            a = math.radians(-90 + side * 35 + k * 18)
            x0, y0 = ex + rx * math.cos(a), ey + ry * math.sin(a)
            p.line(x0, y0, x0 + 0.1 * R * math.cos(a), y0 + 0.12 * R * math.sin(a), INK, 1.0)

    # mouth: open smile with a straight upper lip and a strip of teeth
    my = cy + 0.42 * R
    if pose.mouth == 'smile':
        p.disc(cx, my, 0.4 * R + 1.2, INK, ry=0.24 * R + 1.2)
        p.disc(cx, my, 0.4 * R, INK, ry=0.24 * R)
        for y in range(max(0, int(my - 0.3 * R) - 1), min(p.h, int(my) + 1)):  # cut away the upper half
            for x in range(max(0, int(cx - 0.45 * R) - 1), min(p.w, int(cx + 0.45 * R) + 2)):
                if p.px[y][x] == INK:
                    p.px[y][x] = ORANGE
        p.line(cx - 0.42 * R, my, cx + 0.42 * R, my, INK, 1.4)
        p.disc(cx, my + 0.07 * R, 0.33 * R, white, ry=0.06 * R)  # teeth
    elif pose.mouth == 'talk':
        p.disc(cx, my + 0.08 * R, 0.24 * R, INK, ry=0.06 * R + 0.2 * R * pose.talk)
        if pose.talk > 0.4:
            p.disc(cx, my - 0.02 * R, 0.18 * R, white, ry=0.04 * R)
    elif pose.mouth == 'hmm':
        for i in range(21):
            x = cx - 0.35 * R + 0.7 * R * i / 20
            p.disc(x, my + 0.05 * R + 0.05 * R * math.sin(i * 1.3), 0.7, INK)
    elif pose.mouth == 'whistle':
        p.ring(cx, my + 0.05 * R, 0.09 * R, INK, 1.2)
    else:  # flat
        p.line(cx - 0.3 * R, my + 0.05 * R, cx + 0.3 * R, my + 0.05 * R, INK, 1.3)

    # extras
    for i in range(pose.ripples):
        p.ring(cx + 1.2 * R, cy - 0.7 * R, (0.25 + 0.25 * i) * R, DIM, 0.8, start=-50, end=50)
    if pose.question:
        qx, qy = cx + 1.35 * R, cy - 1.3 * R
        p.ring(qx, qy, 0.16 * R, DIM, 1.0, start=160, end=400)
        p.line(qx, qy + 0.16 * R, qx, qy + 0.32 * R, DIM, 1.0)
        p.dot(qx, qy + 0.48 * R, DIM)


class Clock(Widget):
    """Right-hand panel: the character, drifting slowly, animated at 12 fps."""

    def __init__(self):
        super().__init__(id='right')
        self.state = 'idle'
        self.animator = Animator()
        self.painter = Painter(1, 2)
        self.x = self.y = 0.5
        self.vx, self.vy = random.uniform(-0.04, 0.04), random.uniform(-0.03, 0.03)
        self.last = time.time()

    def on_mount(self):
        self.set_interval(1 / 12, self.tick)

    def set_state(self, state):
        self.state = state

    def tick(self):
        now = time.time()
        dt, self.last = now - self.last, now
        width, height = self.size.width, self.size.height * 2
        if width < 10 or height < 10:
            return
        # character box in pixels: ~3.5R wide (arms), ~3.3R tall (question mark to shoes)
        R = max(6.0, min(width / 3.6, height / 3.4))
        bw, bh = 3.5 * R, 3.3 * R
        self.x += self.vx * dt
        self.y += self.vy * dt
        for attr, v in (('x', 'vx'), ('y', 'vy')):
            value = getattr(self, attr)
            if value < 0 or value > 1:
                setattr(self, v, -getattr(self, v) * random.uniform(0.8, 1.2))
                setattr(self, attr, min(max(value, 0), 1))
        if random.random() < dt * 0.3:
            self.vx = max(-0.06, min(0.06, self.vx + random.uniform(-0.02, 0.02)))
            self.vy = max(-0.05, min(0.05, self.vy + random.uniform(-0.02, 0.02)))
        cx = bw / 2 + self.x * max(0, width - bw)
        cy = 1.5 * R + self.y * max(0, height - bh)
        self.painter = Painter(width, height)
        draw_character(self.painter, cx, cy, R, self.animator.pose(self.state, now), now)
        self.refresh()

    def render_line(self, y):
        if y * 2 >= self.painter.h or self.painter.w != self.size.width:
            return Strip.blank(self.size.width)
        return self.painter.strip(y)


# --- the app --------------------------------------------------------------------------------------------

class SaturdayApp(App):

    CSS = f"""
    Screen {{ layout: horizontal; background: #16100a; color: {CREAM}; }}
    #left {{ width: 1fr; height: 100%; }}
    #right {{ width: 46; height: 100%; border: round {ORANGE}; }}
    #header {{ height: auto; padding: 0 1; border-bottom: solid {DARK}; }}
    #log {{ height: 1fr; padding: 0 1; background: transparent; scrollbar-color: {DARK}; }}
    #chat {{ display: none; border: round {AMBER}; background: #16100a; color: {CREAM}; }}
    #chat.open {{ display: block; }}
    #keys {{ height: 1; padding: 0 1; color: {DIM}; }}
    """
    BINDINGS = [
        Binding('ctrl+t', 'toggle_chat', 'type', priority=True),
        Binding('ctrl+c', 'quit', 'quit', priority=True),
        Binding('ctrl+q', 'quit', 'quit', show=False, priority=True),
        Binding('escape', 'close_chat', show=False),
    ]

    def __init__(self, config, build, log_factory):
        super().__init__()
        self.config = config
        self.build = build  # (log) -> Assistant
        self.log_factory = log_factory  # (sink) -> Log
        self.typed = queue.Queue()
        self.typing = False
        self.pending = False
        self.closing = False
        self.menu = []
        self.state = 'idle'
        self.error = None

    def compose(self):
        with Vertical(id='left'):
            yield Static(id='header')
            yield RichLog(id='log', wrap=True, markup=True, auto_scroll=True)
            yield Input(id='chat', placeholder='type to Saturday, Enter to send')
            yield Static('Ctrl+T type | Ctrl+C quit', id='keys')
        yield Clock()

    def on_mount(self):
        self.title = NAME
        self.update_header()
        self.run_worker(self.converse, thread=True, exit_on_error=False)

    def on_unmount(self):
        self.closing = True  # lets the conversation thread fall out of its listen loop

    # --- ui helpers (main thread) ---

    def update_header(self):
        line = f"[{ORANGE}]* {NAME} - {STATUS[self.state]}[/]"
        if self.pending:
            line += f"   [{AMBER}]waiting for yes / no[/]"
        if self.menu:
            line += f"\n[{DIM}]can: " + ' | '.join(self.menu) + '[/]'
        self.query_one('#header', Static).update(line)

    def set_state(self, state):
        self.state = state
        self.query_one(Clock).set_state(state)
        self.update_header()

    def note(self, kind, text):
        log = self.query_one('#log', RichLog)
        if kind == 'you':
            log.write(f"[bold {AMBER}]You:[/] {text}")
        elif kind == 'saturday':
            log.write(f"[bold {ORANGE}]{NAME}:[/] {text}")
        elif kind == 'tool' and not text.startswith('call '):
            log.write(f"  [{DIM}]{text}[/]")
        elif kind == 'error':
            log.write(f"  [bold red]{text}[/]")
        elif kind == 'wait':
            self.pending = True
            self.update_header()

    def action_toggle_chat(self):
        chat = self.query_one('#chat', Input)
        chat.toggle_class('open')
        if chat.has_class('open'):
            chat.focus()
        else:
            chat.value = ''
            self.typing = False
        self.query_one('#keys', Static).update('Esc close | Enter send' if chat.has_class('open') else 'Ctrl+T type | Ctrl+C quit')

    def action_close_chat(self):
        if self.query_one('#chat', Input).has_class('open'):
            self.action_toggle_chat()

    def on_input_changed(self, event):
        self.typing = bool(event.value)

    def on_input_submitted(self, event):
        text = event.value.strip()
        event.input.value = ''
        self.typing = False
        if text:
            self.typed.put(text)

    # --- conversation (worker thread) ---

    def converse(self):
        ui = self.call_from_thread
        log = self.log_factory(lambda kind, text: ui(self.note, kind, text))
        try:
            assistant = self.build(log)
            self.menu = [p.name.replace('_', ' ') for p in assistant.plugins]
            ui(self.update_header)
            io = None
            if not self.config.text:
                from controls.voice import VoiceIO
                io = VoiceIO(self.config, log, lambda state: ui(self.set_state, state))
        except Exception as error:
            self.error = f"{type(error).__name__}: {error}"
            ui(self.exit)
            return
        session = Session()
        self.say(io, greeting())
        while not self.closing:
            text = self.hear(io)
            if text is None:
                return
            reply, pending = assistant.respond(session, text)
            self.say(io, reply)
            while pending is not None:
                answer = self.hear(io)
                if answer is None:
                    return
                self.pending = False
                reply, pending = assistant.resume(session, is_yes(answer))
                self.say(io, reply)
            if assistant.is_goodbye(text):
                time.sleep(1.0)
                ui(self.exit)
                return

    def hear(self, io):
        # Constant listening: the mic reopens after every silence; typing interrupts it.
        while not self.closing:
            try:
                text = self.typed.get_nowait()
                self.call_from_thread(self.note, 'you', text)
                self.call_from_thread(self.set_state, 'thinking')
                return text
            except queue.Empty:
                pass
            if io is None:
                time.sleep(0.05)
                continue
            text = io.listen(cancel=lambda: self.closing or self.typing or not self.typed.empty())
            if text:
                return text
        return None

    def say(self, io, text):
        if self.closing:
            return
        if io is not None:
            io.say(text)  # logs 'saturday' and drives the speaking state itself
            return
        self.call_from_thread(self.note, 'saturday', text)
        self.call_from_thread(self.set_state, 'speaking')
        time.sleep(min(4.0, 0.6 + len(text) * 0.03))
        if not self.closing:
            self.call_from_thread(self.set_state, 'idle')


class TUI:

    def __init__(self, config, build, log_factory):
        self.app = SaturdayApp(config, build, log_factory)

    def run(self):
        self.app.run()
        if self.app.error:
            raise SystemExit(self.app.error)
