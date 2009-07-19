# characters.py -- character loading and Drop Pattern display/generation
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: characters.py 286 2004-09-04 03:51:59Z piman $"

import os
import math
import pygame
from pygame import transform

import dirstore; dirstore.require("0.1")
from dirstore import DirStore

import config
import random
import load

from constants import *

# Stores information about a character (not a player).
class Character(object):
    def __init__(self, name):
        store = DirStore(name)
        self.drop = DropPattern([s.strip() for s in
                                 store.read("drop").strip().split("\n")])
        self.pattern = self.drop.render()
        self.stats = store.read("description").strip().split("\n")
        if "quips" in store:
            self.quips = store.read("quips").strip().split("\n")
        else:
            self.quips = Character.default.quips
        self.description = self.stats.pop()
        self.name = self.stats.pop(0).strip()
        self.stats.append("Attack: %0.2fx" % self.drop.cost)
        self.images = {}

        for image in ["bl-corner", "bottom-bar", "br-corner", "left-bar",
                      "panel-bg", "portrait", "right-bar", "top-bar",
                      "ul-corner", "ur-corner", "background"]:
            filename = image + ".png"
            if filename in store:
                self.images[image] = pygame.image.load(store.open(filename))
            else:
                self.images[image] = Character.default.images[image]

    # Draw a border, optionally with an image in the center
    def border(self, image):
        # Passing in a sequence fills the image with the character's
        # background.
        if isinstance(image, list) or isinstance(image, tuple):
            img = self.images["panel-bg"]
            surf = pygame.Surface([image[0] + 20, image[1] + 20])
            for x in range(0, image[0], img.get_width()):
                for y in range(0, image[1], img.get_height()):
                    surf.blit(img, [x + 10, y + 10])

        else:
            surf = pygame.Surface([image.get_width() + 20,
                                   image.get_height() + 20])
            surf.blit(image, [10, 10])

        top = self.images["top-bar"]
        bot = self.images["bottom-bar"]
        bot_y = surf.get_height() - 10
        for x in range(0, surf.get_width(), top.get_width()):
            surf.blit(top, [x, 0])
        for x in range(0, surf.get_width(), bot.get_width()):
            surf.blit(bot, [x, bot_y])

        left = self.images["left-bar"]
        right = self.images["right-bar"]
        right_x = surf.get_width() - 10
        for y in range(0, surf.get_height(), left.get_height()):
            surf.blit(left, [0, y])
        for y in range(0, surf.get_height(), right.get_height()):
            surf.blit(right, [right_x, y])

        surf.blit(self.images["ul-corner"], [0, 0])
        surf.blit(self.images["ur-corner"], [right_x, 0])
        surf.blit(self.images["bl-corner"], [0, bot_y])
        surf.blit(self.images["br-corner"], [right_x, bot_y])

        return surf

# The pattern which a character drops gems in.
class DropPattern(object):
    color_map = { "b": "blue", "g": "green", "y": "yellow", "r": "red",
                  "p": "purple", "c": "cyan", "o": "orange" }

    def __init__(self, array):
        self._array = [[DropPattern.color_map[c] for c in s] for s in array]
        self.cost = self._calculate_cost()

    # Given a number of gems to drop, return the actual rows of blocks
    # to be dropped.
    def multiply(self, count):
        rows = []
        array = list(self._array)
        if self.cost < 1: count = int(math.ceil(count * self.cost))
        elif self.cost > 1: count = int(math.floor(count * self.cost))
        while count >= 6:
            rows.append(list(array.pop()))
            array.insert(0, list(rows[-1]))
            count -= 6
        if count != 0:
            possible = [0, 1, 2, 4, 5]
            to_fill = []
            rows.append(list(array.pop()))
            array.insert(0, list(rows[-1]))
            while count > 0 and len(possible) > 0:
                to_fill.append(random.choice(possible))
                possible.remove(to_fill[-1])
                count -= 1

            # Column 3 (where pieces fall) is filled in last
            if count == 1: to_fill.append(3)

            for i in range(len(rows[-1])):
                if i not in to_fill: rows[-1][i] = None
            
        return rows

    # Draw our gem pattern as an image, for the character selection screen.
    def render(self):
        pattern = pygame.Surface([32 * 6, 32 * 4])

        for y, row in enumerate(self._array):
            for x, c in enumerate(row):
                img = load.block(c)
                pattern.blit(img, [32 * x, 32 * y])
        pattern = transform.rotozoom(pattern, 0, 0.8).convert()
        return pattern

    def _calculate_cost(self):
        # Patterns that are more complicated drop less stones, to be
        # fair. Thus, we have to calculate the "randomness" of the drop
        # pattern, and get some kind of multiplier to make it fair. So:
        #
        # For each stone, look at the stones to the left, and below
        # it. If both are the same color, add 1. If neither are the
        # same color, subtract 1. If one is the same and one is
        # different, add 0. This gives us an initial score; higher
        # means the grid is "easier", and so the multiplier should be
        # higher.
        #
        # Thus, -20 is the "worst" (.5x) and 20 is the "best" (2x).
        
        s = 0
        for i in range(4):
            for j in range(5):
                c = self._array[i][j]
                c1 = self._array[(i + 1) % 4][j]
                c2 = self._array[i][j + 1]

                if c1 == c2 == c: s += 1
                elif c1 != c and c2 != c: s -= 1

        if s < 0: return 1 - s / -40.0
        else: return 1 + (s / 20.0)

# Load all characters found in our resource paths
def init():
    char_base = os.path.join(angrydd_path, "characters")
    print char_base
    try:
        Character.default = Character(os.path.join(char_base, "default"))
    except StandardError, s:
        try:
            Character.default = Character(os.path.join(char_base,
                                                       "default.zip"))
        except:
            raise SystemExit("E: Unable to load default character data.")

    dir = os.listdir(char_base)

    avail = []
    arcade = []

    # Remove the secret characters if they aren't unlocked yet.
    #if not config.getboolean("unlock", "unixbros"):
    #    for name in ["cron", "grep"]:
    #        try: dir.remove(name + ".dwarf")
    #        except ValueError: pass
    #        try: dir.remove(name + ".dwarf.zip")
    #        except ValueError: pass

    for name in ["wall", "stallman", "fowler", "kay", "knuth",
                 "torvalds", "pairing-monster"]:
        try:
            name += ".dwarf"
            arcade.append(Character(os.path.join(char_base, name)))
        except StandardError, s:
            try:
                name += ".zip"
                arcade.append(Character(os.path.join(char_base, name)))
            except StandardError, s:
                print "W: Unable to load character %s: %s" % (name, s)
                print "W: Arcade mode disabled."
    
    for name in dir:
        if "dwarf" in name:
            try:
                avail.append(Character(os.path.join(char_base, name)))
            except StandardError, s:
                print "W: Unable to load character %s: %s" % (name, s)
    avail.sort(lambda a, b: cmp(a.name, b.name))
    Character.available = avail
    Character.arcade = arcade
