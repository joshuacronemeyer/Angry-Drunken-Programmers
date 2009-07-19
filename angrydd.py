#!/usr/bin/env python

# angrydd - a falling block puzzle game
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# version 2 along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

__date__ = "$LastChangedDate: 2006-01-12 15:19:27 -0600 (Thu, 12 Jan 2006) $"
__version__   = "1.0.1"
__revision__  = "$Id: angrydd.py 317 2006-01-12 21:19:27Z piman $"
__copyright__ = "Copyright 2004 Joe Wreschnig <piman@sacredchao.net>"
__license__   = "GNU GPL v2"
__author__    = "Joe Wreschnig <piman@sacredchao.net>"

import os
import sys

def print_help():
    print """\
Usage: %s [ --debug | --help | --version ]
Options:
  --help, -h     Print this help message and exit.
  --version, -v  Print version and copyright information and exit.
  --debug        Start without Psyco support, for profiling and debugging.
  --profile      Start with profiling (implies --debug).
""" %(
        sys.argv[0])
    raise SystemExit

def print_version():
    print """\
Angry Drunken Programmers %s - a falling block puzzle game
Copyright 2004 %s

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU GPL version 2, as published
by the Free Software Foundation.""" % (__version__, __author__)
    raise SystemExit

if __name__ == "__main__":
    if ("--help" in sys.argv) or ("-h" in sys.argv): print_help()
    elif ("--version" in sys.argv) or ("-v" in sys.argv): print_version()

angrydd_path = os.path.split(os.path.realpath(__file__))[0]
if os.path.exists(os.path.join(angrydd_path, "angrydd.zip")):
    sys.path.insert(0, os.path.join(angrydd_path, "angrydd.zip"))

import pygame
from pygame import mixer

from constants import *

import config
import load

# Toggling fullscreen doesn't work on non-X11 platforms as of Pygame 1.7.
def toggle_fs():
    flags = 0
    fs = config.getboolean("settings", "fullscreen") ^ True
    if "linux" not in sys.platform:
        if fs: flags ^= FULLSCREEN
        pygame.display.set_mode([800, 600], flags)
    else: pygame.display._toggle_fullscreen()
    config.set("settings", "fullscreen", str(fs))

pygame.display._toggle_fullscreen = pygame.display.toggle_fullscreen
pygame.display.toggle_fullscreen = toggle_fs

def main():
    from characters import Character

    init()

    import menu
    import howtoplay
    import unlocker
    main_menu = [
        ("Dwarf versus Dwarf", menu.entry(play_game, False)),
        ("Arcade Mode", menu.entry(play_arcade_game, False)),
        ("Setup", menu.entry(setup, False)),
        ("How to Play", menu.entry(howtoplay.init, False)),
        ("Quit Game", menu.break_menu)]

    if config.getboolean("unlock", "unlocker"):
        main_menu.insert(3, ("View Unlocks", menu.entry(unlocker.init, False)))

    if config.getboolean("unlock", "single"):
        main_menu.insert(2, ("Single Player",
                             menu.entry(play_single_game, False)))
    if config.getboolean("unlock", "cpuversus"):
        main_menu.insert(2,
                         ("Dwarf versus Robot",
                          menu.entry(play_ai_game, False)))

#    if len(Character.arcade) != 8:
#        main_menu = [main_menu[0]] + main_menu[2:]

    menu.Menu(main_menu)
    quit()

# Start a player vs. player game
def play_game(menu, platform, pos, key):
    import game, charselect
    characters = charselect.init()
    if characters[0] is not None:
        game.VersusGame(characters)
        mixer.music.load(os.path.join("music", "intro.ogg"))
        mixer.music.play(-1)
    return True

# Start a single player game
def play_single_game(menu, platform, pos, key):
    import game
    game.SingleGame()
    mixer.music.load(os.path.join("music", "intro.ogg"))
    mixer.music.play(-1)
    return True

# Start a game versus an AI
def play_ai_game(menu, platform, pos, key):
    import game, charselect
    characters = charselect.init()
    if characters[0] is not None:
        game.AIGame(characters)
        mixer.music.load(os.path.join("music", "intro.ogg"))
        mixer.music.play(-1)
    return True

def play_arcade_game(menu, platform, pos, key):
    import game, charselect
    characters = charselect.init(numplayers = 1)
    if characters[0] is not None:
        game.ArcadeGame(characters)
        mixer.music.load(os.path.join("music", "intro.ogg"))
        mixer.music.play(-1)
    return True

# Open the configuration menu
def setup(menu_, platform, pos, key):
    import menu
    config_menu = [
        (config.get_matches(), menu.entry(config.set_matches)),
        (config.get_speed(), menu.entry(config.set_speed)),
        (config.get_rotup(), menu.entry(config.set_rotup)),
        (config.get_space(), menu.entry(config.set_space)),

        ("Back", menu.break_menu)
        ]

    if config.getboolean("unlock", "cpuversus"):
        config_menu.insert(2, (config.get_ai(), menu.entry(config.set_ai)))

    if config.getboolean("unlock", "combat"):
        config_menu.insert(-1, (config.get_combat(),
                                menu.entry(config.set_combat)))

    try: menu.Menu(config_menu)
    except menu.MenuExit: pass
    return True

# Set up Pygame, load sounds, etc.
def init():
    if os.name == 'posix': # We need to force stereo in many cases.
        try: mixer.pre_init(44100, -16, 2)
        except pygame.error: pass

    pygame.init()
    config.init(rc_file)
    os.chdir(angrydd_path)
    pygame.display.set_caption("Angry, Drunken Programmers")
    try: pygame.display.set_icon(pygame.image.load("angrydd.png"))
    except pygame.error: pass
    pygame.mouse.set_visible(False)
    if config.getboolean("settings", "fullscreen"): flags = FULLSCREEN
    else: flags = 0
    pygame.display.set_mode([800, 600], flags)

    import game
    import menu
    import boxes
    import characters

    boxes.TickBox.sound = load.sound("tick.wav")
    boxes.TickBox.sound.set_volume(0.3)

    boxes.BreakBox.sound = load.sound("break.wav")
    boxes.BreakBox.sound.set_volume(0.3)

    boxes.Special.sound = load.sound("select-confirm.wav")
    boxes.Special.sound.set_volume(0.5)

    game.FallingBoxes.rotate_sound = load.sound("rotate.wav")
    game.FallingBoxes.rotate_sound.set_volume(0.2)

    menu.Menu.bg = load.image("menu-bg.png").convert()

    characters.init()

    mixer.music.load(os.path.join("music", "intro.ogg"))
    mixer.music.play(-1)

# Shut down Pygame, save configuration data, turn on the Unlocker.
def quit(*args):
    pygame.quit()
    print "Saving configuration."
    config.unlock("unlocker")
    if int(config.get("scores-versus-3", "1").split(",")[1]) > 20000:
        config.unlock("single")
    config.write(file(rc_file, "w"))
    raise SystemExit

if __name__ == "__main__":
    profile = ("--profile" in sys.argv)
    debug = profile or ("--debug" in sys.argv)
    double_ai = ("--double-ai" in sys.argv)

    if not debug:
        try:
            import psyco
            psyco.full()
            print "Psyco optimizing compiler found. Using psyco.full()."
        except ImportError: pass

    if profile:
        import profile
        profile.run("main()")
    elif double_ai:
        # Hack to run two AIs versus each other; use --double-ai AI1,Ai2
        # on the command line. Bypasses main(), very buggy, for testing
        # use only.
        init()
        ai1, ai2 = sys.argv[sys.argv.index("--double-ai") + 1].split(",")
        game.AIGame([Character.available[0], Character.available[0]],
                     all_ais = True, ai1 = ai1, ai2 = ai2)
    else: main()
