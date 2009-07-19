# constants.py -- constants for angrydd
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: constants.py 295 2005-08-13 07:22:00Z piman $"

# This file is designed to import via 'from constants import *'.
# Accordingly, this really should only contain constants and nothing else!

import os
from pygame.locals import *

angrydd_path = os.path.split(os.path.realpath(__file__))[0]

# Using 'isdir' here causes problems on filesystems that can read
# .zip files as directories.
if angrydd_path.lower().endswith(".zip"):
    angrydd_path = os.path.split(angrydd_path)[0]

if os.name == "posix" and "HOME" in os.environ:
    rc_file = os.environ["HOME"] + "/.angryddrc"
else: rc_file = os.path.join(angrydd_path, "angryddrc")

PLAYER, PAUSE = range(USEREVENT + 1, USEREVENT + 3)

# Each of these must have a corresponding file in images/<color>.png,
# images/<color>-crash.png.
COLORS = ["blue", "green", "red", "yellow", "purple", "cyan", "orange"]

# Translate event keys.
UP, LEFT, RIGHT, DOWN, ROT_CW, ROT_CC, CONFIRM = range(7)

# Combat specials.
HEALTHY, CLEAR, REVERSE, FLIP, BLINK, GRAY, SCRAMBLE = range(7)

# AI difficulties
STUPID, VEASY, EASY, NORMAL, HARD, INSANE = range(6)

CREDITS = [
    "Angry, Drunken Programmers",
    "Code & Design by Joe Wreschnig",
    "Music by theGREENzebra and JZig",
    "Characters by Zach Welhouse",
    "Portraits by Jessi Silver",
    "Additional Art by Jenn Hartnoll",
    "Voices by Chris Thorp",
    "Thanks to testers/helpers:",
    "antont, "
    "asterick, "
    "CrashChaos, ",
    "drewp, "
    "illume, "
    "jacius, "
    "Knio, ",
    "mindy, "
    "mojo, "
    "mu, "
    "Safiiru, ",
    "ShredWheat, "
    "sku, "
    "stargazer, ",
    "wm_eddie, "
    "yossarian, ",
    "people at MAS, "
    "and more I forgot."
    ]
