# textfx.py -- funky textual effects
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: textfx.py 286 2004-09-04 03:51:59Z piman $"

import pygame
import math
import load

from constants import *

# From the Pygame font effect contest, by Pete Shinners. Displays
# some waving text.
class TextWavey(object):
    def __init__(self, size, message, fontcolor, amount = 10):
        self.base = shadow(message, size, color = fontcolor)
        self.steps = range(0, self.base.get_width(), 2)
        self.amount = amount
        self.size = self.base.get_rect().inflate(0, amount).size
        self.offset = 0.0

    def animate(self):
        s = pygame.Surface(self.size, SRCALPHA, 32)
        s.fill([0, 0, 0, 0])
        height = self.size[1]
        self.offset += 0.5
        for step in self.steps:
            src = Rect(step, 0, 2, height)
            dst = src.move(0, math.cos(self.offset + step*.02) * self.amount)
            s.blit(self.base, dst, src)
        return s

# A font capable of wrapping text at a given width.
class WrapFont(object):

    # size is the (integer) size of the font to create. width is the
    # maximum width of the rendered surface.
    def __init__(self, size, width):
        self._font = pygame.font.Font(None, size)
        self._width = width
        self._ls = self._font.get_linesize()
        self._ds = - self._font.get_descent()

    def get_linesize(self): return self._ls

    # Return the number of lines a bit of text will require.
    def lines(self, text):
        lines = 1
        words = text.split()
        start = 0
        for i in range(len(words)):
            line = " ".join(words[start:i+1])
            if self._font.size(line)[0] > self._width:
                lines += 1
                start = i
        return lines

    # Return the total size of Surface that render will return for
    # the given text.
    def size(self, text):
        return [self._width, self.lines(text) * self._ls + self._ds]
 
    # Render some text, optionally with shadowing.
    def render(self, text, color = [255, 255, 255], shdw = True):
        lines = []
        words = text.split()
        start = 0
        for i in range(len(words)):
            line = " ".join(words[start:i+1])
            if self._font.size(line)[0] > self._width:
                line = " ".join(words[start:i])
                if shdw: t = shadow(line, self._font, color)
                else: t = self._font.render(line, True, color)
                lines.append(t)
                start = i
        line = " ".join(words[start:])
        if shdw: t = shadow(line, self._font, color)
        else: t = self._font.render(line, True, color)
        lines.append(t)
 
        image = pygame.Surface([self._width,
                                len(lines) * self._ls + self._ds],
                               SRCALPHA, 32)
        image.fill([0, 0, 0, 0])
        for i, line in enumerate(lines):
            image.blit(line, [0, i * self._ls])
        return image

# Shadow some text (by 1 pixel). Resulting shadow is down and to
# the left, and 1/10th as bright.
def shadow(string, font, color = [255, 255, 255]):
    if isinstance(font, int): font = pygame.font.Font(None, font)
    t1 = font.render(string, True, color)
    t2 = font.render(string, True, [c / 10 for c in color])
    srf = pygame.Surface([t1.get_width() + 1, t1.get_height() + 1],
                         SRCALPHA, 32)
    srf.blit(t2, [1, 1])
    srf.blit(t1, [0, 0])
    return srf

# Render a box, and put a (shadowed) character inside it.
def lettered_box(char, clr):
    img = load.block(clr)
    t = shadow(char, 32)
    img.blit(t, t.get_rect(center = [15, 15]))
    return img

# Generate a pile of boxes from a string, split on spaces, one word
# per line. The color is random.
def boxes_from_string(string, pos = None):
    lines = string.split(" ")
    img = pygame.Surface([32 * max(map(len, lines)), 32 * len(lines)])
    colors = ["blue", "red", "green", "orange", "purple"]
    if pos is not None: clr = colors[pos % len(colors)]
    else: clr = random.choice(colors)

    for i, string in enumerate(lines):
        limg = pygame.Surface([32 * len(string), 32])
        for j, letter in enumerate(string):
            nimg = lettered_box(letter, clr)
            limg.blit(nimg, [j * 32, 0])
        r = limg.get_rect(midtop = [img.get_rect().centerx, 32 * i])
        img.blit(limg, r)
    return img
