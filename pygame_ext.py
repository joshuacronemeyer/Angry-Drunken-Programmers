# pygame_ext.py -- extensions to Pygame for angrydd
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: pygame_ext.py 286 2004-09-04 03:51:59Z piman $"

import os
import util
from pygame import mixer, error, time

# Override the standard mixer_music methods with ones that can
# fail gracefully if the mixer can't start or the music file
# is missing.
def new_load(filename):
    try: mixer.music._load(filename)
    except error:
        print ("W: Unable to load %s" % filename),
        if os.path.exists(filename): print "(is your soundcard in use?)"
        else: print "(where's the full sounds/ directory?)"
        pass

def new_play(loop):
    try: mixer.music._play(loop)
    except error: pass

def new_fadeout(time):
    try: mixer.music._fadeout(time)
    except error: pass

mixer.music._load = mixer.music.load
mixer.music._play = mixer.music.play
mixer.music._fadeout = mixer.music.fadeout
mixer.music.load = new_load
mixer.music.play = new_play
mixer.music.fadeout = new_fadeout

# Override time.get_ticks() to subtract an offset; this allows simple
# pausing of game for all objects using get_ticks().
time._get_ticks = time.get_ticks
time.paused = False
time.__start_pause = 0
time.__at_pause = 0
time.__offset = 0

time.clock = util.WaitClock()

def pause():
    if not time.paused:
        time.__start_pause = time._get_ticks()
        time.__at_pause = time.get_ticks()
        time.paused = True
time.pause = pause

def unpause():
    if time.paused:
        time.__offset += time._get_ticks() - time.__start_pause
        time.paused = False
time.unpause = unpause

def toggle_pause():
    if time.paused: time.unpause()
    else: time.pause()
time.toggle_pause = toggle_pause

def new_get_ticks():
    if time.paused: return time.__at_pause
    else: return time._get_ticks() - time.__offset
time.get_ticks = new_get_ticks

# Override Sound. This returns a dummy object when the sound file could
# not be loaded (busy soundcard, missing file, bad SDL_mixer...)
mixer._Sound = mixer.Sound
def new_Sound(filename):
    try: return mixer._Sound(filename)
    except error:
        print ("W: Unable to load %s" % filename),
        return FakeSound()

mixer.Sound = new_Sound

# Pretend to be a sound. FIXME: There might be some way to check
# function arity and detect more calling problems ahead of time.
class FakeSound(object):
    def __getattr__(self, name):
        if not isinstance(mixer._Sound, type) or hasattr(mixer._Sound, name):
            if name.startswith("get_"): return (lambda *args: 0)
            else: return (lambda *args: None)
        else: raise AttributeError, name
