# events.py -- event handling wrapper
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: events.py 317 2006-01-12 21:19:27Z piman $"

from constants import *
from pygame import event, key, joystick, time, display
from pygame.event import Event

from util import Singleton

# Key repeat delay and repeat rate and joystick tolerance.
DELAY, RATE = 200, 75
TOLERANCE = 0.95

import config

CONFIRM_BUTTON = config.getint("buttons", "start")
PAUSE_BUTTON = config.getint("buttons", "pause")

# Alias post, so pygame.event is unnecessary outside this module.
post = event.post

class EventManager(Singleton):
    def __init__(self):
        if hasattr(EventManager, "_singleton"): return
        key.set_repeat(DELAY, RATE)
        event.set_allowed(None)
        event.set_allowed([KEYDOWN, JOYBUTTONDOWN, JOYAXISMOTION,
                           JOYBUTTONUP, PLAYER])

        for i in range(joystick.get_count()):
            joystick.Joystick(i).init()

        # Information for joystick repeat.
        self._last_press = [None, None]
        self._last_press_start = [0, 0]
        self._last_press_times = [0, 0]

        # Maps key values to player numbers.
        self.players = { K_w: 0, K_a: 0, K_s: 0, K_d: 0, K_q: 0, K_e: 0,
                         K_i: 1, K_j: 1, K_k: 1, K_l: 1, K_u: 1, K_o: 1,
                         K_LEFT: 0, K_RIGHT: 0, K_UP: 0, K_DOWN: 0,
                         K_SPACE: 0, K_KP_ENTER: 0, K_RETURN: 0, K_2: 1,
                         K_1: 0, K_BACKSPACE: 1 }

        # Maps key values to internal event keys.
        self.events = { K_w: UP, K_a: LEFT, K_s: DOWN, K_d: RIGHT,
                        K_q: ROT_CC, K_e: ROT_CW,
                        K_i: UP, K_j: LEFT, K_k: DOWN, K_l: RIGHT,
                        K_u: ROT_CC, K_o: ROT_CW,
                        K_LEFT: LEFT, K_RIGHT: RIGHT, K_UP: UP, K_DOWN: DOWN,
                        K_SPACE: ROT_CC, K_KP_ENTER: CONFIRM,
                        K_RETURN: CONFIRM, K_2: CONFIRM,
                        K_BACKSPACE: CONFIRM, K_1: CONFIRM }

        Singleton.__init__(self)

    def clear(self):
        self._last_press = [None, None]
        self._last_press_start = [0, 0]
        self._last_press_times = [0, 0]
        event.clear()

    # This isn't a very good "wait" function.
    def wait(self):
        while not event.peek([KEYDOWN, JOYBUTTONDOWN, JOYAXISMOTION,
                              JOYBUTTONUP, QUIT]):
            time.wait(10)
        return self.get()

    # Get all events in the Pygame event queue and translate them
    # to PLAYER events.
    def get(self):
        t = time.get_ticks()
        events = []
        for ev in event.get(KEYDOWN):
            try:
                events.append(Event(PLAYER,
                                    key = self.events[ev.key],
                                    player = self.players[ev.key]))
            except KeyError:
                if ev.key == K_F11 or ev.key == K_f:
                    display.toggle_fullscreen()
                elif ev.key == K_p:
                    events.append(Event(PAUSE))
                elif ev.key == K_ESCAPE:
                    events.append(Event(QUIT))

        # Joysticks are translated to either 0 or 1, and any button
        # below 4 is also translated to 0 or 1. Thus, e.g. button 3
        # on js 1 and button 1 on js 3 will generate the same event.

        # Button numbers over 15 swap the joystick value and have
        # 16 subtracted from them. This makes the EMSUSB2 adapter work
        # in Linux (where it appears as a single 32 button joystick,
        # rather than two 16 button ones).

        # Button patterns testing on Playstation controllers and also
        # a Gravis gamepad.
        for ev in event.get(JOYBUTTONDOWN):
            if ev.button > 15: button, joy = ev.button - 16, ev.joy + 1
            else: button, joy = ev.button, ev.joy
            player = joy % 2
            if button == CONFIRM_BUTTON:
                events.append(Event(PLAYER, key = CONFIRM, player = player))
            elif button == PAUSE_BUTTON:
                events.append(Event(PAUSE))
            elif button < 4:
                if button & 1: key = ROT_CW
                else: key = ROT_CC
                self._last_press[player] = key
                self._last_press_start[player] = t
                events.append(Event(PLAYER, key = key, player = player))

        for ev in event.get(JOYBUTTONUP):
            if ev.button > 15: button, joy = ev.button - 16, ev.joy + 1
            else: button, joy = ev.button, ev.joy
            player = joy % 2
            if button < 4:
                if button & 1: key = ROT_CW
                else: key = ROT_CC
                if self._last_press[player] == key:
                    self._last_press[player] = None

        # Axis stuff; again for the EMSUSB2 axes 3 and 4 are actually on
        # the second joystick.
        for ev in event.get(JOYAXISMOTION):
            if ev.axis == 3: axis, joy = 0, ev.joy + 1
            elif ev.axis == 4: axis, joy = 1, ev.joy + 1
            else: axis, joy = ev.axis, ev.joy
            player = joy % 2
            key = None
            if axis == 0:
                if ev.value < -TOLERANCE: key = LEFT
                elif ev.value > TOLERANCE: key = RIGHT
            elif axis == 1:
                if ev.value > TOLERANCE: key = DOWN
                elif ev.value < -TOLERANCE: key = UP

            if key is not None and self._last_press[player] != key:
                self._last_press[player] = key
                self._last_press_start[player] = t
                events.append(Event(PLAYER, key = key, player = player))
            elif key is None and axis <= 1:
                self._last_press[player] = None

        # Check for repeated events -- if any player has a pending
        # repeat event that hasn't fired in the given interval put it
        # on the queue again.
        for player in range(len(self._last_press)):
            if (self._last_press[player] is not None and
                (t - self._last_press_start[player]) > DELAY and
                (t - self._last_press_times[player]) > RATE):
                self._last_press_times[player] = t
                events.append(Event(PLAYER, key = self._last_press[player],
                                    player = player))

        # Don't actually post events here; the loop that gets them
        # knows what to do. However, if PLAYER events are posted, grab them
        # and use them.
        events.extend(event.get([PLAYER, QUIT]))
        return events
