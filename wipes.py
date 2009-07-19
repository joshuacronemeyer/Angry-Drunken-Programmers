# wipes.py - a set of simple screen wipes (in and out)
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: wipes.py 286 2004-09-04 03:51:59Z piman $"

import random
from pygame import display, draw, time, Rect, Surface
from itertools import chain

c = time.Clock()

def line_out_l2r():
    screen = display.get_surface()
    w, h = screen.get_size()
    for x in chain(xrange(0, w, 2), xrange(w - 1, 0, -2)):
        display.update(draw.line(screen, [0, 0, 0], [x, 0], [x, h]))
        c.tick(700)

def line_out_r2l():
    screen = display.get_surface()
    w, h = screen.get_size()
    for x in chain(xrange(w - 1, 0, -2), xrange(0, w, 2)):
        display.update(draw.line(screen, [0, 0, 0], [x, 0], [x, h]))
        c.tick(700)

def line_out_t2b():
    screen = display.get_surface()
    w, h = screen.get_size()
    for y in chain(xrange(0, h, 2), xrange(h - 1, 0, -2)):
        display.update(draw.line(screen, [0, 0, 0], [0, y], [w, y]))
        c.tick(700)

def line_out_b2t():
    screen = display.get_surface()
    w, h = screen.get_size()
    for y in chain(xrange(h - 1, 0, -2), xrange(0, h, 2)):
        display.update(draw.line(screen, [0, 0, 0], [0, y], [w, y]))
        c.tick(700)

def line_in_l2r(surf):
    screen = display.get_surface()
    w, h = screen.get_size()
    for x in chain(xrange(0, w, 2), xrange(w - 1, 0, -2)):
        display.update(screen.blit(surf, [x, 0, 1, h], [x, 0, 1, h]))
        c.tick(700)

def line_in_r2l(surf):
    screen = display.get_surface()
    w, h = screen.get_size()
    for x in chain(xrange(w - 1, 0, -2), xrange(0, w, 2)):
        display.update(screen.blit(surf, [x, 0, 1, h], [x, 0, 1, h]))
        c.tick(700)

def line_in_t2b(surf):
    screen = display.get_surface()
    w, h = screen.get_size()
    for y in chain(xrange(0, h, 2), xrange(h - 1, 0, -2)):
        display.update(screen.blit(surf, [0, y, w, 1], [0, y, w, 1]))
        c.tick(700)

def line_in_b2t(surf):
    screen = display.get_surface()
    w, h = screen.get_size()
    for y in chain(xrange(h - 1, 0, -2), xrange(0, h, 2)):
        display.update(screen.blit(surf, [0, y, w, 1], [0, y, w, 1]))
        c.tick(700)

OUTS = [line_out_l2r, line_out_r2l, line_out_b2t, line_out_t2b]
INS = [line_in_l2r, line_in_r2l, line_in_b2t, line_in_t2b]

def wipe_out(): random.choice(OUTS)()
def wipe_in(s): random.choice(INS)(s)
