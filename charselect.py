# charselect.py -- character selection screen
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: charselect.py 286 2004-09-04 03:51:59Z piman $"

import pygame
from pygame.sprite import Sprite, RenderUpdates

import textfx
import wipes
import load

from events import EventManager
from characters import Character

from constants import *

# Display the character selection screen; return the two selected
# characters (or None, None when escape was pressed).
def init(numplayers = 2):
    screen = pygame.display.get_surface()
    em = EventManager()
    bg = load.image("select-bg.png")
    move_snd = load.sound("select-move.wav")
    confirm_snd = load.sound("select-confirm.wav")
    confirm_snd.set_volume(0.4)

    sprites = RenderUpdates()
    portraits = [PortraitDisplay([20, 20]), PortraitDisplay([20, 320])]
    names = [NameDisplay([20, 220]), NameDisplay([20, 520])]
    drops = [DropDisplay([240, 20]), DropDisplay([240, 320])]
    stats = [StatDisplay([240, 150]), StatDisplay([240, 450])]
    descs = [DescDisplay([430, 20]), DescDisplay([430, 320])]
    char_sprites = zip(portraits, names, drops, stats, descs)

    idx = [0, 0]
    confirmed = [False, False]
    for i, sprs in enumerate(char_sprites):
        if i < numplayers:
            for spr in sprs: spr.set_char(Character.available[i])
            sprites.add(sprs)
            idx[i] = i

    init_bg = bg.convert()
    sprites.update(pygame.time.get_ticks())
    sprites.draw(init_bg)
    wipes.wipe_in(init_bg)
    init_bg = None # Let us GC it
    pygame.display.update()
    sprites.clear(screen, bg)

    while False in [(c.confirmed or i >= numplayers)
                    for i, c in enumerate(portraits)]:
        for ev in em.wait():
            if ev.type == PLAYER:
                if ev.key == LEFT:
                    i = (idx[ev.player] - 1) % len(Character.available)
                    idx[ev.player] = i
                elif ev.key == RIGHT:
                    i = (idx[ev.player] + 1) % len(Character.available)
                    idx[ev.player] = i
                elif ev.key in [ROT_CC, ROT_CW, CONFIRM]:
                    confirm_snd.play()
                    portraits[ev.player].confirmed = True

                if ev.key in [LEFT, RIGHT]:
                    move_snd.play()
                    for spr in char_sprites[ev.player]:
                        spr.set_char(Character.available[idx[ev.player]])
                    portraits[ev.player].confirmed = False

            elif ev.type == QUIT:
                return None, None

        sprites.update(pygame.time.get_ticks())
        pygame.display.update(sprites.draw(screen))
        sprites.clear(screen, bg)

    return [Character.available[i] for i in idx]

# A character portrait, 200x200 image.
class PortraitDisplay(Sprite):
    def __init__(self, topleft):
        Sprite.__init__(self)
        self.rect = Rect([topleft, [200, 200]])
        self._light = pygame.Surface([180, 180])
        self._light.fill([255, 255, 255])
        self._dark = pygame.Surface([180, 180])
        self._dark.fill([0, 0, 0])
        self.confirmed = False

    def set_char(self, char):
        charimage = char.images["portrait"].convert()
        charimage.set_alpha(130)
        self._dark = pygame.Surface([180, 180])
        self._dark.fill([0, 0, 0])
        self._dark.blit(charimage, [0, 0])
        self._dark = char.border(self._dark)

        charimage.set_alpha(256)
        self._light = pygame.Surface([180, 180])
        self._light.blit(charimage, [0, 0])
        self._light = char.border(self._light)

    def update(self, time):
        if self.confirmed: self.image = self._light
        else: self.image = self._dark

# The character's name
class NameDisplay(Sprite):
    def __init__(self, topleft):
        Sprite.__init__(self)
        self._topleft = topleft

    def set_char(self, char):
        self.image = textfx.shadow(char.name, 50)
        self.rect = self.image.get_rect(topleft = self._topleft)

# A display of the character's drop gem pattern.
class DropDisplay(Sprite):
    def __init__(self, topleft):
        Sprite.__init__(self)
        self._topleft = topleft

    def set_char(self, char):
        self.image = char.border(char.drop.render())
        self.rect = self.image.get_rect(topleft = self._topleft)

# Display statistics about the character.
class StatDisplay(Sprite):
    def __init__(self, topleft):
        Sprite.__init__(self)
        self._topleft = topleft
        self._fsize = 30
        self._height = pygame.font.Font(None, self._fsize).get_linesize()

    def set_char(self, char):
        stats = char.stats
        y = self._height * len(stats) + self._height/2
        self.image = pygame.Surface([400, y], SRCALPHA, 32)

        for i, stat in enumerate(stats):
            self.image.blit(textfx.shadow(stat, self._fsize),
                            [0, i * self._height])
        self.rect = self.image.get_rect(topleft = self._topleft)

# A description of the character. If the description is too long, it
# overflows off the screen...
class DescDisplay(Sprite):
    def __init__(self, topleft):
        Sprite.__init__(self)
        self._topleft = topleft
        self._font = textfx.WrapFont(18, 310)

    def set_char(self, char):
        text = self._font.render(char.description)
        self.image = char.border([text.get_width() + 20,
                                  text.get_height() + 20])
        self.image.blit(text, [20, 20])
        self.rect = self.image.get_rect(topleft = self._topleft)
