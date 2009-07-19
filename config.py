# config.py -- ConfigFile proxy/wrapper module
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: config.py 291 2004-09-09 00:38:52Z piman $"

import os
from ConfigParser import ConfigParser
from constants import *

_config = ConfigParser()

# Alias various ConfigParser functions.
getboolean = _config.getboolean
getint = _config.getint
set = _config.set
get = _config.get

_unlocked = {}

# Set up default options and high scores, then load the real
# config file (if it exists).
def init(rc_file):
    _config.add_section("settings")
    _config.set("settings", "rotate_on_up", "yes")
    _config.set("settings", "rotate_on_space", "yes")
    _config.set("settings", "matches", "3")
    _config.set("settings", "ai", "2")
    _config.set("settings", "speed", "750")
    _config.set("settings", "combat", "no")
    _config.set("settings", "fullscreen", "yes")

    _config.add_section("buttons")
    _config.set("buttons", "start", "9")
    _config.set("buttons", "pause", "8")

    _config.add_section("unlock")
    for c in ["unlocker", "unixbros", "combat", "single", "cpuversus"]:
        _config.set("unlock", c, "no")

    _config.add_section("scores-single")
    for n, name, score in [(1, "Ogi", 1000),
                           (2, "Gnarr", 500),
                           (3, "Thane", 0)]:
        _config.set("scores-single", str(n), "%s,%d" % (name, score))

    _config.add_section("scores-versus-arcade")
    for n, name, score in [(1, "Ogi", 1000),
                           (2, "Gnarr", 500),
                           (3, "Thane", 0)]:
        _config.set("scores-versus-arcade", str(n), "%s,%d" % (name, score))

    for c in range(1, 10, 2):
        _config.add_section("scores-versus-%d" % c)
        for n, name, score in [(1, "Ogi", 1000),
                               (2, "Gnarr", 500),
                               (3, "Thane", 0)]:
            _config.set("scores-versus-%d" % c, str(n),
                       "%s,%d" % (name, score))

    if os.name == "posix": rc_file = os.environ["HOME"] + "/.angryddrc"
    else: rc_file = "angryddrc"
    _config.read([rc_file])

    if _config.getboolean("settings", "rotate_on_space") is False:
        from events import EventManager
        EventManager().events[K_SPACE] = DOWN

# Unlock things, but delay until game quit.
def unlock(thing): _unlocked[thing] = True

def write(*args):
    for key in _unlocked: _config.set("unlock", key, "yes")
    _config.write(*args)

# Set various options "intelligently". Up/down change the option,
# Confirm increases it but wraps from the highest value to the lowest.

def set_matches(menu, platform, pos, key):
    m = _config.getint("settings", "matches")
    if key == CONFIRM: m = (m + 2) % 10
    elif key == UP or key == ROT_CW: m = min(9, m + 2)
    else: m = max(1, m - 2)
    _config.set("settings", "matches", str(m))
    platform.text = get_matches()
    return False

def get_matches():
    m = _config.getint("settings", "matches")
    return "Best %d/%d" % ((m / 2) + 1, m)

def set_speed(menu, platform, pos, key):
    s = _config.getint("settings", "speed")
    if key == CONFIRM:
        if s == 250: s = 1250
        else: s -= 250
    elif key == UP or key == ROT_CW: s = max(250, s - 250)
    else: s = min(1250, s + 250)
    _config.set("settings", "speed", str(s))
    platform.text = get_speed()
    return False

def get_speed():
    return { 250: "Very Fast", 500: "Fast", 750: "Normal Speed",
             1000: "Slow", 1250: "Very Slow"
             }[_config.getint("settings", "speed")]

def set_rotup(menu, platform, pos, key):
    r = _config.getboolean("settings", "rotate_on_up")
    r ^= True
    _config.set("settings", "rotate_on_up", str(r).lower())
    platform.text = get_rotup()
    return False

def get_rotup():
    if _config.getboolean("settings", "rotate_on_up"): return "Up Rotates"
    else: return "Up Doesn't Rotate"

def set_space(menu, platform, pos, key):
    r = _config.getboolean("settings", "rotate_on_space")
    r ^= True
    _config.set("settings", "rotate_on_space", str(r).lower())
    from events import EventManager
    if r: EventManager().events[K_SPACE] = ROT_CC
    else: EventManager().events[K_SPACE] = DOWN
    platform.text = get_space()
    return False

def get_space():
    if _config.getboolean("settings", "rotate_on_space"):
        return "Space Rotates"
    else: return "Space Drops"

def set_combat(menu, platform, pos, key):
    r = _config.getboolean("settings", "combat")
    r ^= True
    _config.set("settings", "combat", str(r).lower())
    platform.text = get_combat()
    return False

def get_combat():
    if _config.getboolean("settings", "combat"): return "Combat Blocks"
    else: return "No Combat Blocks"

def set_ai(menu, platform, pos, key):
    m = _config.getint("settings", "ai")
    if key == CONFIRM: m = (m + 1) % 6
    elif key == UP or key == ROT_CW: m = min(5, m + 1)
    else: m = max(0, m - 1)
    _config.set("settings", "ai", str(m))
    platform.text = get_ai()
    return False

def get_ai():
    return "AI: %s" % ["Stupid", "Very Easy", "Easy", "Normal",
                       "Hard", "Insane"][_config.getint("settings", "ai")]
