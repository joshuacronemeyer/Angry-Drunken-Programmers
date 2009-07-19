# unlocker.py -- display information about unlocked game features
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: unlocker.py 286 2004-09-04 03:51:59Z piman $"

import pygame

import config
import textfx
import wipes

from characters import Character
from events import EventManager

from constants import *

# Display help text for unlocked features. This includes a lot of
# verbatim text we should move to a data file somewhere.
def init(*args):
    em = EventManager()
    disp = pygame.Surface([800, 600])

    disp.fill([0, 0, 0])
    font = textfx.WrapFont(30, 760)
    bg = Character.default.border([780, 100]).convert()

    bg.set_alpha(256)
    disp.blit(bg, [0, 0])
    t = font.render(
        "Welcome to the unlock screen! As you do more in this "
        "game, new features will sometimes appear. By playing the "
        "game at least once, you've managed to unlock this unlock "
        "screen, for example. Keep practicing, and more things will "
        "appear...")

    disp.blit(t, t.get_rect(midleft = [20, 60]))

    if config.getboolean("unlock", "single"):
        bg.set_alpha(256)
        disp.blit(bg, [0, 120])
        t = font.render(
            "Congratulations! By scoring over 20,000 points in a 2/3 versus "
            "match, you've unlocked single player mode. It's a lot "
            "harder, so you should practice your crystal building and "
            "combo setups.")
        disp.blit(t, t.get_rect(midleft = [20, 180]))
    else:
        bg.set_alpha(127)
        disp.blit(bg, [0, 120])

    if config.getboolean("unlock", "unixbros"):
        bg.set_alpha(256)
        disp.blit(bg, [0, 240])
        t = font.render(
            "By breaking a crystal of over 16 gems, you've unlocked two more "
            "characters - The Yuniks brothers. Both encourage a very "
            "unique style of attacks. Go check them out.")
        disp.blit(t, t.get_rect(midleft = [20, 300]))
    else:
        bg.set_alpha(127)
        disp.blit(bg, [0, 240])

    if config.getboolean("unlock", "combat"):
        bg.set_alpha(256)
        disp.blit(bg, [0, 360])
        t = font.render(
            "By getting at least a 4 chain, you've unlocked combat "
            "mode. If this is on, special attack rocks might appear in "
            "versus mode, that have strange effects on the other "
            "player. Enable it in the setup menu.")
        disp.blit(t, t.get_rect(midleft = [20, 420]))
    else:
        bg.set_alpha(127)
        disp.blit(bg, [0, 360])

    if config.getboolean("unlock", "cpuversus"):
        bg.set_alpha(256)
        disp.blit(bg, [0, 480])
        t = font.render(
            "You've made it at least halfway through arcade mode! "
            "You can now practice against any dwarf, on any "
            "of the AI levels.")
        disp.blit(t, t.get_rect(midleft = [20, 540]))
    else:
        bg.set_alpha(127)
        disp.blit(bg, [0, 480])

    wipes.wipe_in(disp)
    pygame.display.update()
    quit = False
    while not quit:
        for ev in em.wait():
             quit = (quit or
                     ev.type == QUIT or
                     (ev.type == PLAYER and
                      ev.key in [ROT_CC, ROT_CW, CONFIRM]))

    return True
