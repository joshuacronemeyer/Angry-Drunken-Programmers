# menu.py -- display/use the game and configuration menu
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: menu.py 306 2005-10-06 19:46:26Z piman $"

import pygame
from pygame.sprite import Sprite, RenderUpdates

import config
import textfx
import load

from util import Singleton
import events; from events import EventManager

from constants import *

# One of the carts displayed in the game menus.
class Platform(Sprite):
    def __init__(self, midbottom, string, pos):
        Sprite.__init__(self)
        self._pos = pos
        self.rect = Rect([0, 0, 0, 0])
        self.rect.midbottom = midbottom
        self.text = string
        self._lastx = self._goalx = self.rect.left
        self._ntime = 0

    # Set the text on the cart, using lettered box.es
    def _set_text(self, string):
        midbottom = self.rect.midbottom
        plat = load.image("platform.png")
        plat.set_colorkey(plat.get_at([0, 0]), RLEACCEL)
        plat_r = plat.get_rect()
        letters = textfx.boxes_from_string(string, pos = self._pos)
        surf = pygame.Surface([max(260, letters.get_width()),
                                   plat.get_height() + letters.get_height()])
        plat_r.centerx = surf.get_rect().centerx
        plat_r.bottom = surf.get_height() - 1
        surf.blit(plat, plat_r)
        letters_r = letters.get_rect()
        letters_r.centerx = surf.get_rect().centerx
        letters_r.bottom = surf.get_height() - 16
        surf.blit(letters, letters_r)
        surf.set_colorkey(surf.get_at([0, 0]), RLEACCEL)
        self.image = surf
        self.rect = self.image.get_rect()
        self.rect.midbottom = midbottom

    text = property(None, _set_text)

    # Move the cart to the left.
    def left(self):
        t = pygame.time.get_ticks()
        self._ntime = t + 600
        self._goalx += 260
        self._lastx = self.rect.left

    # Move it to the right.
    def right(self):
        t = pygame.time.get_ticks()
        self._ntime = t + 600
        self._goalx -= 260
        self._lastx = self.rect.left

    def update(self, time):
        if time < self._ntime:
            p = (self._ntime - time) / 600.0
            self.rect.left = self._goalx - (self._goalx - self._lastx) * p
        else: self.rect.left = self._goalx

# Top score display
class TopScores(Sprite, Singleton):
    def __init__(self):
        Sprite.__init__(self)
        self._start = pygame.time.get_ticks()
        self.read_scores()
        Singleton.__init__(self)

    # Load all the scores from the configuration data.
    def read_scores(self):
        self._images = []
        secs = []
        for c in range(1, 10, 2):
            sec = "scores-versus-%d" % c
            name = "Top Scores: Best %d/%d" % (c / 2 + 1, c)
            secs.append((sec, name))
        if config.getboolean("unlock", "single"):
            secs.append(("scores-single", "Top Scores: Single Player"))
        secs.append(("scores-versus-arcade", "Top Scores: Arcade"))

        for sec, name in secs:
            img = pygame.Surface([420, 110], SRCALPHA, 32)
            img.fill([0, 0, 0, 0])
            t = textfx.shadow(name, 26)
            img.blit(t, t.get_rect(midtop = [210, 0]))
            for i in range(1, 4):
                parts = config.get(sec, str(i)).split(",")
                score = parts.pop()
                name = ",".join(parts)
                tl = textfx.shadow(name, 30)
                tr = textfx.shadow(score, 30)
                img.blit(tl, tl.get_rect(topleft = [10, 25 * i]))
                img.blit(tr, tr.get_rect(topright = [415, 25 * i]))
            self._images.append(img)
        self.image = self._images[0]
        self.rect = self.image.get_rect(midtop = [400, 440])

    def update(self, time):
        # Switch displayed scores every 4 seconds.
        time = time % (4000 * len(self._images))
        self.image = self._images[int(time / 4000)]


# A menu; a bunch of boxes displayed on carts, with callbacks
class Menu(object):
    def __init__(self, items):
        platforms = [Platform([400 + 260 * i, 390], s[0], i)
                     for i, s in enumerate(items)]
        credits = Credits()
        self._score = TopScores()
        sprites = RenderUpdates([credits, self._score])
        sprites.add(platforms)

        pos = 0
        em = EventManager()
        em.clear()
        screen = pygame.display.get_surface()

        em.get()
        quit = False

        screen.blit(Menu.bg, [0, 0])
        sprites.draw(screen)
        pygame.display.update()
        
        while not quit:
            for ev in em.get():
                if ev.type == PLAYER:
                    if ev.key == LEFT:
                        if pos != 0:
                            pos -= 1
                            for p in platforms: p.left()
                    elif ev.key == RIGHT:
                        if pos != len(items) - 1:
                            pos += 1
                            for p in platforms: p.right()
                    else:
                        try:
                            r = items[pos][1][ev.key](self, platforms[pos],
                                                      pos, ev.key)
                            if r:
                                # If the callback returns true, then we
                                # need to redraw the whole screen and
                                # reread our scores. (If it returns false,
                                # it probably means it just modified some
                                # cart text).
                                self._score.read_scores()
                                screen.blit(Menu.bg, [0, 0])
                                pygame.display.update()
                        except KeyError: pass

                elif ev.type == QUIT: quit = True

            sprites.update(pygame.time.get_ticks())
            pygame.display.update(sprites.draw(screen))
            sprites.clear(screen, Menu.bg)
            pygame.time.clock.tick(60)

# The most common kind of menu entry, a single callback function
# that we call when certain keys are pressed.
def entry(f, dirs = True):
    if dirs: return { UP: f, DOWN: f, ROT_CC: f, ROT_CW: f, CONFIRM: f }
    else:  return { ROT_CC: f, ROT_CW: f, CONFIRM: f }

# A "go back" callback function. By posting a QUIT event to the queue,
# the menu will exit and go to the previous screen.
break_menu = entry(lambda *args: pygame.event.post(pygame.event.Event(QUIT)),
                   False)

# A sprite displaying a small credits banner in the lower-left corner.
class Credits(Sprite, Singleton):
    def __init__(self, lines = CREDITS):
        Sprite.__init__(self)
        self._lines = [textfx.shadow(i, 20, [255, 255, 255]) for i in lines]
        self._idx = 0
        self._update = pygame.time.get_ticks() + 7000
        self._w = 220
        self._h = 19
        self.update(pygame.time.get_ticks())

    def update(self, t):
        self.image = pygame.Surface([self._w, self._h], SRCALPHA, 32)
        self.rect = self.image.get_rect(bottomleft = [0, 600])
        if self._update - t > 1000:
            txt = self._lines[self._idx]
            r = txt.get_rect(center = [self._w / 2, self._h / 2])
            self.image.blit(txt, r)
        elif t < self._update:
            p = (self._update - t) / 1000.0
            wy = int(self._h * p)
            idx1 = self._idx
            idx2 = (self._idx + 1) % len(self._lines)
            txt1 = self._lines[idx1]
            txt2 = self._lines[idx2]
            r1 = txt1.get_rect()
            r2 = txt2.get_rect()
            r2.centerx = r1.centerx = self._w / 2
            r2.top = wy
            r1.bottom = wy
            self.image.blit(txt1, r1)
            self.image.blit(txt2, r2)
        else:
            self._idx = (self._idx + 1) % len(self._lines)
            self._update = t + 4000
            txt = self._lines[self._idx]
            r = txt.get_rect(center = [self._w / 2, self._h / 2])
            self.image.blit(txt, r)
