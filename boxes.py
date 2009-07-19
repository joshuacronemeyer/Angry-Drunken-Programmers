# boxes.py -- sundry boxes and box-like things for the game
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: boxes.py 286 2004-09-04 03:51:59Z piman $"

import pygame
from pygame import transform
from pygame.sprite import Sprite

import textfx
import random
import config
import load

from constants import *

# Abstract class from which other block types inherit.
class AbstractBox(object):
    def __init__(self, color, topleft):
        self.size = [1, 1]      # How big are we; [1,1] except for Box.
        self.color = color
        self.x, self.y = topleft
        self._ntime = None
        self.crashed = False     # If we've been hit by a crash gem/diamond.

    # Accessors for coordinates. FIXME: Make these properties.
    def _get_top(self): return self.y
    def _get_bottom(self): return self.y + self.size[1]
    def _get_left(self): return self.x
    def _get_right(self): return self.x + self.size[0]

    # Blocks adjacent to it on the top...
    def _adj_top(self, field):
        adj = []
        if self.y != 0:
            for x in range(self.x, self._get_right()):
                adj.append(field[self.y - 1][x])
        return filter(None, adj)

    # And so on.
    def _adj_bottom(self, field):
        adj = []
        b = self._get_bottom()
        if b != field.height:
            for x in range(self.x, self._get_right()):
                adj.append(field[b][x])
        return filter(None, adj)

    def _adj_left(self, field):
        adj = []
        if self.x != 0:
            for y in range(self.y, self._get_bottom()):
                adj.append(field[y][self.x - 1])
        return filter(None, adj)

    def _adj_right(self, field):
        adj = []
        r = self._get_right()
        if r != field.width:
            for y in range(self.y, self._get_bottom()):
                adj.append(field[y][r])
        return filter(None, adj)

    # All blocks adjacent to this one.
    def adjacent(self, field):
        adj = self._adj_left(field)
        adj.extend(self._adj_right(field))
        adj.extend(self._adj_top(field))
        adj.extend(self._adj_bottom(field))
        return adj

    # Kill the sprite, and remove it from the field map.
    def remove_from(self, field):
        self.crashed = True
        for x in range(self.x, self._get_right()):
            for y in range(self.y, self._get_bottom()):
                field[y][x] = None

    # Check if something is below us on the field (or we're at the bottom).
    def is_blocked_down(self, field):
        bot = self._get_bottom()
        if bot == field.height: return True
        else:
            for x in range(self.x, self._get_right()):
                if field[bot][x] is not None: return True
            return False

    # Actually move down space.
    def fall(self, field):
        bot = self._get_bottom()
        for x in range(self.x, self._get_right()):
            field[self.y][x] = None
            field[bot][x] = self
        self.y += 1

    # Move to an entirely new location. This is done when blocks are
    # moved from a FallingBlock onto the field.
    def move(self, xy):
        self.x, self.y = xy

    # Destroy self if appropriate; return the value of the gems
    # destroyed.
    def crash(self, field, gem, immed = False):
        broken = 0
        if not self.crashed and gem.color == self.color:
            broken += self.size[0] * self.size[1] * (sum(self.size) / 2)
            self.crashed = True
            for box in self.adjacent(field):
                broken += box.crash(field, self)
            if self.size != [1, 1]:
                field.max_gemsize = max(field.max_gemsize,
                                        self.size[0] * self.size[1])
        return broken

# A generator for random boxes.
class BoxGen(object):
    def __init__(self, rand, colors, single):
        self.rand = rand
        self.combat = (config.getboolean("settings", "combat") and not single)
        self.colors = colors

    def get(self, topleft):
        f = self.rand.random()
        color = self.rand.choice(self.colors)
        if self.combat:
            if f <= 0.004: return DiamondSprite("diamond", topleft)
            elif f <= 0.20: return BreakBoxSprite(color, topleft)
            elif f <= 0.27: return SpecialSprite(color, topleft)
            else: return BoxSprite(color, topleft)
        else:
            if f <= 0.006: return DiamondSprite("diamond", topleft)
            elif f <= 0.20: return BreakBoxSprite(color, topleft)
            else: return BoxSprite(color, topleft)

# Find all instances of a given type in a sequence.
def instances_in(sequence, typ):
    return filter(lambda x: isinstance(x, typ), sequence)

class SpriteBox(Sprite):
    def __init__(self, color, type = ""):
        Sprite.__init__(self)
        self._image = load.block(color, type)
        self._image.set_colorkey(self._image.get_at([0, 0]), RLEACCEL)
        self.image = transform.scale(self._image,
                                     [self.size[0] * 32, self.size[1] * 32])
        self._ckey = self._image.get_colorkey()
        self.rect = self.image.get_rect(topleft = [self.x * 32, self.y * 32])
        self._btime = 0

    def fall(self, field): self.rect.topleft = [self.x * 32, self.y * 32]
    def move(self, xy): self.rect.topleft = [xy[0] * 32, xy[1] * 32]

    def update(self, time):        
        if self.crashed and time > self._btime:
            for i in range(15):
                start = random.randrange(4)
                end = random.randrange(4)
                if end == start: end = (end + 1) % 4
                
                if start == 1: start = [random.randrange(32), 0]
                elif start == 2: start = [random.randrange(32), 31]
                elif start == 3: start = [0, random.randrange(32)]
                elif start == 0: start = [31, random.randrange(32)]
                
                if end == 1: end = [random.randrange(32), 0]
                elif end == 2: end = [random.randrange(32), 31]
                elif end == 3: end = [0, random.randrange(32)]
                elif end == 0: end = [31, random.randrange(32)]

                pygame.draw.line(self._image, self._ckey, start, end)

            self.image = transform.scale(self._image,
                                         [self.size[0] * 32,
                                          self.size[1] * 32])
            self._btime = time + 20


# A basic box type; grows when put near other boxes in the field.
class Box(AbstractBox):
    # Resize ourselve, and put ourself in the right place in the
    # field. Note that our topleft doesn't change, since the most
    # topleft gem is always the one resized.
    def set_size(self, size, field):
        self.size = size
        for x in range(self.x, self._get_right()):
            for y in range(self.y, self._get_bottom()):
                field[y][x] = self

    # Try to form larger blocks; return the blocks removed from merging.
    def try_merge(self, field):
        if self.size == [1,1]:
            # Special case the 1,1 size, because we don't want 2x1 or 1x2
            # blocks forming.
            if self.x == field.width - 1 or self.y == field.height - 1:
                return []
            b1 = field[self.y][self.x + 1]
            b2 = field[self.y + 1][self.x]
            b3 = field[self.y + 1][self.x + 1]
            if (isinstance(b1, Box) and isinstance(b2, Box) and
                isinstance(b3, Box) and
                self.color == b1.color == b2.color == b3.color and
                b1.size == b2.size == b3.size == [1, 1]):
                # Remove the sprites from the field and its sprite group
                b1.remove_from(field)
                b2.remove_from(field)
                b3.remove_from(field)
                self.set_size([2, 2], field)
                return [b1, b2, b3]
        else:
            # test all four directions
            blocks = self._adj_top(field)
            # there are blocks above us, and they are not special blocks,
            # and they are the same color, and they all share the same
            # top location, the leftmost border and rightmost border
            # match up with ours. We need these last checks to avoid
            # oddly shaped structures like
            # XXYY merging into XZZY
            #  ZZ                ZZ
            if (len(blocks) == self.size[0] and
                len(instances_in(blocks, Box)) == len(blocks) and
                [b.color for b in blocks].count(self.color) == len(blocks) and
                not [b for b in blocks if b.y != blocks[0].y] and
                blocks[0].x == self.x and
                blocks[-1]._get_right() == self._get_right()):
                dead = []
                for b in blocks:
                    b.remove_from(field)
                    dead.append(b)
                bot = self._get_bottom()
                self.y = blocks[0].y
                self.set_size([self.size[0], bot - self.y], field)
                return dead

            blocks = self._adj_bottom(field)
            if (len(blocks) == self.size[0] and
                len(instances_in(blocks, Box)) == len(blocks) and
                [b.color for b in blocks].count(self.color) == len(blocks) and
                not [b for b in blocks if
                     b._get_bottom() != blocks[0]._get_bottom()] and
                blocks[0].x == self.x and
                blocks[-1]._get_right() == self._get_right()):
                dead = []
                for b in blocks:
                    b.remove_from(field)
                    dead.append(b)
                bot = blocks[0]._get_bottom()
                self.set_size([self.size[0],  bot - self.y], field)
                return dead

            blocks = self._adj_left(field)
            if (len(blocks) == self.size[1] and
                len(instances_in(blocks, Box)) == len(blocks) and
                [b.color for b in blocks].count(self.color) == len(blocks) and
                not [b for b in blocks if b.x != blocks[1].x] and
                blocks[0].y == self.y and
                blocks[-1]._get_bottom() == self._get_bottom()):
                dead = []
                for b in blocks:
                    b.remove_from(field)
                    dead.append(b)
                right = self._get_right()
                self.x = blocks[0].x
                self.set_size([right - self.x, self.size[1]], field)
                return dead

            blocks = self._adj_right(field)
            if (len(blocks) == self.size[1] and
                len(instances_in(blocks, Box)) == len(blocks) and
                [b.color for b in blocks].count(self.color) == len(blocks) and
                not [b for b in blocks if
                     b._get_right() != blocks[0]._get_right()] and
                blocks[0].y == self.y and
                blocks[-1]._get_bottom() == self._get_bottom()):
                dead = []
                for b in blocks:
                    b.remove_from(field)
                    dead.append(b)
                right = blocks[0]._get_right()
                self.set_size([right - self.x, self.size[1]], field)
                return dead

        return []

# A version of the above that can be displayed on the screen.
class BoxSprite(Box, SpriteBox):
    def __init__(self, color, topleft):
        Box.__init__(self, color, topleft)
        SpriteBox.__init__(self, color, "")

    def move(self, xy):
        Box.move(self, xy)
        self.rect.topleft = [self.x * 32, self.y * 32]

    def fall(self, field):
        Box.fall(self, field)
        SpriteBox.fall(self, field)

    def set_size(self, size, field):
        Box.set_size(self, size, field)
        self.image = load.gem(self.color, self.size[0], self.size[1])
        self.rect = self.image.get_rect(topleft = [self.x * 32, self.y * 32])

# A gem that breaks gems of the same color when it lands by them.
class BreakBox(AbstractBox):
    # Called by the field to see if we can break anything.
    # THIS DOESN'T BREAK SELF! self will break when its
    # crashed method gets called by the gem *it* breaks.
    def try_crash(self, field):
        broken = 0
        for box in self.adjacent(field):
            broken += box.crash(field, self, True)
        return broken

class BreakBoxSprite(BreakBox, SpriteBox):
    def __init__(self, color, topleft):
        BreakBox.__init__(self, color, topleft)
        SpriteBox.__init__(self, color, "-crash")

    def fall(self, field):
        BreakBox.fall(self, field)
        SpriteBox.fall(self, field)

    def move(self, xy):
        BreakBox.move(self, xy)
        SpriteBox.move(self, xy)

# Now when you say special...
# These are the blocks used in "combat" mode, they don't form crystals,
# and when they break you get the 'item' in them.
class Special(AbstractBox):
    names = ["", "cleared", "reversed", "flipped", "blinking",
             "incoming", "scrambled"]
    
    def __init__(self, color, topleft, special = None):
        AbstractBox.__init__(self, color, topleft)
        self.special = (special or random.randint(1, 6))

    def crash(self, field, gem, immed = False):
        if not self.crashed:
            v = AbstractBox.crash(self, field, gem, immed)
            if self.crashed: field.pick_up(self.special)
        else: v = 0
        return v

class SpecialSprite(Special, SpriteBox):
    def load(cls, type):
        if type == SCRAMBLE:
            return textfx.shadow("? ?", 20, [255, 255, 255])
        else:
            fn = ["", "clear", "reverse", "flip", "blink", "gray"][type]
            return load.image("special-%s.png" % fn)

    load = classmethod(load)

    def __init__(self, color, topleft):
        Special.__init__(self, color, topleft)
        SpriteBox.__init__(self, color, "")
        self.image.blit(SpecialSprite.load(self.special), [6, 6])

    def fall(self, field):
        Special.fall(self, field)
        SpriteBox.fall(self, field)

    def move(self, xy):
        Special.move(self, xy)
        SpriteBox.move(self, xy)

# Diamonds break all of the color they land on, but "specially" -
# no bonuses for larger gems. So we just count the number of
# spaces of that color on the field, and then remove them.
# Extend BreakBox so that we find Diamonds when we filter for
# break boxes to crash.
class Diamond(BreakBox):
    def try_crash(self, field):
        broken = 0
        self.crashed = True
        if self.y == field.height - 1:
            field.tech_bonus()
            return 0
        else: color = field[self.y + 1][self.x].color

        for y in range(field.height):
            for x in range(field.width):
                box = field[y][x]
                if (isinstance(box, Box) or isinstance(box, BreakBox) or
                    isinstance(box, Special)):
                    if box.color == color:
                        broken += 1
                        box.crashed = True
                elif isinstance(box, TickBox):
                    if box.color == color:
                        broken += 0.5
                        box.crashed = True
        return broken

class DiamondSprite(Diamond, SpriteBox):
    def __init__(self, color, topleft):
        Diamond.__init__(self, color, topleft)
        SpriteBox.__init__(self, "diamond", "")

    def fall(self, field):
        Diamond.fall(self, field)
        SpriteBox.fall(self, field)

    def move(self, xy):
        Diamond.move(self, xy)
        SpriteBox.move(self, xy)

# Box with a counter on it. When it counts down, it replaces itself
# with a normal Box.
class TickBox(AbstractBox):
    def __init__(self, color, topleft):
        AbstractBox.__init__(self, color, topleft)
        self._time_left = 5

    def _get_time_left(self): return self._time_left
    def _set_time_left(self, timeleft):
        self._time_left = timeleft
        self._render()

    time_left = property(_get_time_left, _set_time_left)

    def tick(self):
        self.time_left -= 1

    def _render(self): pass

    def crash(self, field, gem, immed = False):
        # Tick boxes don't crash adjacent boxes, though they do
        # get destroyed themselves. They are also destroyed irrespective
        # of color.
        if not self.crashed and not immed:
            self.crashed = True
            return 0.5
        else: return 0.0

class TickBoxSprite(TickBox, SpriteBox):
    numerals = []

    def __init__(self, color, topleft):
        TickBox.__init__(self, color, topleft)
        SpriteBox.__init__(self, color, "")
        if not TickBoxSprite.numerals:
            f = pygame.font.Font(None, 32)
            for i in range(6):
                img = textfx.shadow(str(i + 1), f, [200, 200, 200])
                TickBoxSprite.numerals.append(img)
        self._render()

    def move(self, xy):
        TickBox.move(self, xy)
        SpriteBox.move(self, xy)

    def fall(self, field):
        TickBox.fall(self, field)
        SpriteBox.fall(self, field)

    def _render(self):
        self.image = pygame.Surface([32, 32])
        self.image.blit(self._image, [0, 0])
        t = TickBoxSprite.numerals[self._time_left - 1]
        self.image.blit(t, t.get_rect(center = [15, 15]))
        self.image.set_colorkey(self.image.get_at([0, 0]))        
        self.rect = self.image.get_rect(topleft = [self.x * 32, self.y * 32])
