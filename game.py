# game.py -- main game loop, player handling, field display, etc.
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: game.py 317 2006-01-12 21:19:27Z piman $"

import os
import random
import pygame; import pygame_ext

from pygame.sprite import Sprite, RenderUpdates
from pygame.color import Color
from pygame import mixer, transform

from constants import *

import events; from events import Event, EventManager
from boxes import Box, TickBox, BreakBox, Special, Diamond, BoxGen
from boxes import BoxSprite, TickBoxSprite, SpecialSprite

from characters import Character

import textfx
import config
import wipes
import load
import util

# Manage boning counter for single player mode. Keep track of the number
# of turns and blocks left, and drop the blocks (randomly) when that
# number reaches 0. This replaces DropPattern in single player.
class TensionBoner(object):
    def __init__(self):
        self.turns_left = 10
        self.turns_left_max = 10
        self.next_boning = 2
        self.next_boning_max = 2

    # A piece hit the bottom
    def tick(self):
        self.turns_left -= 1

    # The player cleared some gems.
    def debone(self, player, val):
        self.next_boning -= val
        if self.next_boning <= 0:
            player.score.score += (-50 * self.next_boning)
            self.next_boning_max = self.next_boning_max * (5.0/3.0)
            self.turns_left_max += 2
            self.next_boning = int(self.next_boning_max)
            player.score.score += 100 * self.turns_left
            self.turns_left = self.turns_left_max
        return 0

    # No turns left. Drop random blocks.
    # This shares a lot of code with the DropPattern algorithm.
    def bone(self):
        count = self.next_boning
        rows = []
        while count >= 15:
            rows.append([random.choice(COLORS) for i in range(15)])
            count -= 15
        if count != 0:
            possible = range(15)
            to_fill = []
            rows.append([random.choice(COLORS) for i in range(15)])
            while count > 0 and len(possible) > 0:
                to_fill.append(random.choice(possible))
                possible.remove(to_fill[-1])
                count -= 1

            for i in range(len(rows[-1])):
                if i not in to_fill: rows[-1][i] = None
            
        self.next_boning_max = self.next_boning_max * (1.5)
        self.turns_left_max += 2
        self.next_boning = int(self.next_boning_max)
        self.turns_left = self.turns_left_max
        return rows

# Display messages over the field when things happen. Usually a chain,
# but sometimes other things.
class ChainText(Sprite):
    def __init__(self, center):
        Sprite.__init__(self)
        self._center = center
        self._font = pygame.font.Font(None, 48)
        self._blank = pygame.Surface([0, 0])
        self._ntime = 0
        self.image = self._blank
        self.rect = self.image.get_rect()

    def set_chain(self, chain):
        if chain > 1: self.set_text("%d chain!" % chain)

    def set_text(self, text):
        self._ntime = pygame.time.get_ticks() + 1000
        self.image = self._font.render(text, True, [255, 255, 255])
        self.rect = self.image.get_rect()
        self.rect.center = self._center

    chain = property(None, set_chain)
    text = property(None, set_text)

    def update(self, time):
        if self._ntime and time > self._ntime:
            self.image = self._blank
            self.rect = self.image.get_rect()
            self._ntime = None

# The boxes that fall down with time.
class FallingBoxes(Sprite):
    # Orientation/rotation rules:
    # There are 4 possible orientations for the boxes:
    #  2
    #  1 21  1  12    (left to right, rotate counter-clockwise)
    #        2
    #
    #  0  1  2  3

    def __init__(self, box1, box2, field):
        Sprite.__init__(self)
        self.y = 0
        self.x = int(field.width / 2)
        self._box1 = box1
        self._box2 = box2
        self._orient = 0
        self.locked = False
        self._field = field
        self._ntime = None
        self.bonus = False
        self._render()

    # This sprite just appeared on the screen and is now falling.
    def start(self, time): self._ntime = time + 750

    # Predicates to see if we're blocked in the directions we want to go.
    def _is_blocked_left(self):
        l = self._get_left()
        return ((l == 0) or
                (self._field[self._get_top()][l - 1] or
                 self._field[self._get_bottom()][l - 1]))

    def _is_blocked_right(self):
        r = self._get_right()
        return ((r == self._field.width - 1) or
                (self._field[self._get_top()][r + 1] or
                 self._field[self._get_bottom()][r + 1]))

    def _is_blocked_down(self):
        b = self._get_bottom()
        return ((b == self._field.height - 1) or
                (self._field[b + 1][self._get_left()] or
                 self._field[b + 1][self._get_right()]))

    # Actually go right or left, after checking.
    def go_left(self):
        if not (self.locked or self._is_blocked_left()): self.x -= 1
    def go_right(self):
        if not (self.locked or self._is_blocked_right()): self.x += 1

    # Go down. If we can't go down, lock ourself in place.
    def go_down(self):
        if not self._is_blocked_down():
            self._ntime = pygame.time.get_ticks() + self._field.speed
            self.y += 1
        else:
            self.locked = True
            self.bonus = True

    def _get_top(self): return max(0, self.y - int(self._orient == 0))
    def _get_left(self): return self.x - int(self._orient == 1)
    def _get_bottom(self): return self.y + int(self._orient == 2)
    def _get_right(self): return self.x + int(self._orient == 3)

    # Drop our contained boxes onto the field and let them fall.
    def deposit(self):
        if self._orient == 0:
            self._field.add_box([self.x, self.y], self._box1)
            if self.y != 0:
                self._field.add_box([self.x, self.y - 1], self._box2)
        elif self._orient == 1:
            self._field.add_box([self.x, self.y], self._box1)
            self._field.add_box([self.x - 1, self.y], self._box2)
        elif self._orient == 2:
            self._field.add_box([self.x, self.y], self._box1)
            self._field.add_box([self.x, self.y + 1], self._box2)
        elif self._orient == 3:
            self._field.add_box([self.x, self.y], self._box1)
            self._field.add_box([self.x + 1, self.y], self._box2)
        return self._box1, self._box2

    # When a falling block can't rotate properly, the boxes are
    # swapped instead of rotated.
    def _swap(self): self._box1, self._box2 = self._box2, self._box1

    # Try to rotate the piece; push it away from a wall if we need to;
    # swap if we can't. Takes the new orientation and as an argument.
    def _rotate(self, new_o):
        if self.locked: return
        blocked = False
        pushable = False
        dx, dy = 0, 0
        if new_o == 3:
            blocked = (self._get_right() == self._field.width - 1 or
                       self._field[self.y][self.x + 1] is not None)
            pushable = (blocked and
                        self._get_left() != 0 and
                        self._field[self.y][self.x - 1] is None)
            dx = -1
        elif new_o == 0:
            blocked = (self._field[self.y - 1][self.x] is not None)
            pushable = (blocked and
                        self._field[self.y + 1][self.x] is None)
            dy = 1
        elif new_o == 1:
            blocked = (self._get_left() == 0 or
                       self._field[self.y][self.x - 1] is not None)
            pushable = (blocked and
                        self._get_right() != self._field.width - 1 and
                        self._field[self.y][self.x + 1] is None)
            dx = 1
        elif new_o == 2:
            blocked = (self.y == self._field.height - 1 or
                       self._field[self.y + 1][self.x] is not None)

        FallingBoxes.rotate_sound.play()
        if blocked and not pushable:
            self._swap()
        else:
            if pushable:
                self.x += dx
                self.y += dy
            self._orient = new_o
        self._render()

    # Rotate clockwise or counterclockwise.
    def rot_cw(self): self._rotate((self._orient - 1) % 4)
    def rot_cc(self): self._rotate((self._orient + 1) % 4)

    def update(self, time):
        if self._ntime is None: return
        if time > self._ntime:
            if self._is_blocked_down():
                self.locked = True
            else:
                self.y += 1
                self._ntime = time + self._field.speed

        self.rect.left = self.x * 32
        if self._orient == 1: self.rect.left -= 32
        self.rect.top = self.y * 32
        if self._orient == 0: self.rect.top -= 32
        off = float(self._ntime - time) / self._field.speed
        self.rect.top -= int(off * 32)

    # Draw the boxes.
    def _render(self):
        if self._orient & 1 == 0: self.image = pygame.Surface([32, 64])
        else: self.image = pygame.Surface([64, 32])
        self.image.set_colorkey(self.image.get_at([0, 0]))

        if self._orient == 0:
            self.image.blit(self._box1.image, [0, 32])
            self.image.blit(self._box2.image, [0, 0])
        elif self._orient == 1:
            self.image.blit(self._box1.image, [32, 0])
            self.image.blit(self._box2.image, [0, 0])
        elif self._orient == 2:
            self.image.blit(self._box1.image, [0, 0])
            self.image.blit(self._box2.image, [0, 32])
        elif self._orient == 3:
            self.image.blit(self._box1.image, [0, 0])
            self.image.blit(self._box2.image, [32, 0])

        self.rect = self.image.get_rect()

# A simple non-graphical playing field.
class BasicField(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.max_gemsize = 0
        self.max_chain = 0
        self._field = [[None] * width for i in range(height)]

    def __getitem__(self, i): return self._field[i]
    def __iter__(self): return iter(self._field)

    def add_box(self, xy, box):
        box.move(xy)
        self._field[box.y][box.x] = box

    # Move all pieces down one step; return True if pieces moved
    # or False otherwise.
    def fall(self):
        could_move = False
        for i in range(len(self._field) - 2, -1, -1):
            # Things on the first row won't fall, so we don't
            # need to check it.
            for j, box in enumerate(self._field[i]):
                if (box and not box.is_blocked_down(self)):
                    box.fall(self)
                    could_move = True
        return could_move

    # Tick all ticking boxes; replace them if their time runs out.
    def tick(self, Box = Box):
        tickers = filter(lambda b: isinstance(b, TickBox),
                         util.flatten(self._field))
        extickers = []
        for t in tickers:
            t.tick()
            if t.time_left == 0:
                t.remove_from(self)
                extickers.append(t)
                b = Box(t.color, [t.x, t.y])
                self.add_box([t.x, t.y], b)
        return tickers, extickers

    def pick_up(self, special): pass

    # BasicField doesn't know what a "player" is, so it can't
    # give a bonus.
    def tech_bonus(self): pass

    # Try to merge boxes into bigger ones; return True if one
    # merged successfully (only merges one)
    def merge(self):
        boxes = filter(lambda b: isinstance(b, Box),
                       util.flatten(self._field))
        boxes.sort(lambda a, b: cmp(b.y, a.y) and cmp(a.x, b.x))
        for box in boxes:
            dead = box.try_merge(self)
            if len(dead) > 0: return dead
        return []

    # Break everything that will break; return the "value" of
    # the broken 
    def breaking(self):
        breakers = filter(lambda b: isinstance(b, BreakBox),
                          util.flatten(self._field))
        killed_count = sum([b.try_crash(self) for b in breakers
                            if not b.crashed])
        dead = filter(lambda b: b and b.crashed, util.flatten(self._field))
        for box in dead: box.remove_from(self)
        return killed_count, dead

# Graphics for the above field, and a state machine to manage gameplay.
class Field(BasicField, Sprite):
    # The six stages of each "turn":
    # 1. A piece is dropping down and the player can control it (FALLING).
    # 2. The piece hits. Any loose pieces must be dropped downwards.
    #    (FIXING1)
    # 3. TICKING. Any timer block, must tick.
    # 4. MERGING. Large gems form out of smaller ones.
    # 5. BREAKING. Any breaking gems take effect.
    # 6. Stuff breaks. Loose pieces drop (FIXING2).
    # 7. Go to 4) until 6 makes no changes.
    # 8. Drop blocks from opponent's clears. (BONING)
    # 9. Move blocks down one if possible. (BONING2)    
    #    Repeat until player is boned again or no movement.
    # 11. Insert the new falling block. Start again from 1).
    FALLING, FIXING1, TICKING, MERGING, BREAKING, FIXING2, BONING, BONING2 = range(8)

    def __init__(self, player, width = 6, height = 13):
        BasicField.__init__(self, width, height)
        Sprite.__init__(self)
        self._sprites = RenderUpdates()
        self.falling = None
        self._break_time = None
        self.speed = config.getint("settings", "speed")
        self._field = [[None] * width for i in range(height)]
        self._player = player
        self.state = Field.FIXING1
        self._insrow = int((width / 2))
        self._ntime = pygame.time.get_ticks()
        self._broke_any_last = False
        self._killed = 0
        self._disease = HEALTHY
        self._disease_end = 0
        self._chain = 0

        self.rect = Rect([player.topleft, [width*32 + 20, height*32 + 20]])
        # Darken a bit of the screen and use that for our background
        black = pygame.Surface([width * 32, height * 32]).convert()
        black.set_alpha(160)
        screen = pygame.display.get_surface()
        bg = pygame.Surface([width * 32, height * 32]).convert()
        bg.blit(screen, [-player.topleft[0] - 10, -player.topleft[1] - 10])
        bg.blit(black, [0, 0])

        self._outline = player.char.border(bg)
        self._chain_spr = ChainText([int((width / 2.0) * 32) + 10,
                                     int((height / 2.0) * 32) + 10])

        self._render()
        self._state_calls = [self._state_falling,
                             self._state_fixing1,
                             self._state_ticking,
                             self._state_merging,
                             self._state_breaking,
                             self._state_fixing2,
                             self._state_boning,
                             self._state_boning2
                             ]

    # Someone used a special on us...
    def inflict(self, disease):
        if disease == SCRAMBLE:
            self._player._next_disp.scramble()
        elif disease == GRAY:
            row = ["gray", "gray", None, None, None, None]
            random.shuffle(row)
            self._player.enqueue([row])
        elif disease == BLINK:
            self._disease = disease
            self._disease_end = pygame.time.get_ticks() + 30000
        else:
            self._disease = disease
            self._disease_end = pygame.time.get_ticks() + 10000
        self._chain_spr.text = Special.names[disease] + "!"

    def _get_image(self):
        if self._disease == FLIP:
            return transform.flip(self._image, False, True)
        elif self._disease == BLINK:
            # V*V*(3-V-V), V is a value 0-1, flattens the curve around 0-1
            # without using sin or cos.
            t = (pygame.time.get_ticks() % 3000) / 1500.0
            t = abs(t - 1)
            t = t * t * (3 - t - t)
            self._image.set_alpha(int(256 * t))
            return self._image
        else: return self._image

    image = property(_get_image)

    def clear(self):
        self._field = [[None] * self.width for i in range(self.height)]
        self._sprites.empty()

    def _render(self):
        image = pygame.Surface([self.width * 32, self.height * 32])
        image.set_colorkey(image.get_at([0, 0]))
        self._sprites.draw(image)
        if self.falling:
            image.blit(self.falling.image, self.falling.rect)
        self._image = pygame.Surface([self.width * 32 + 20,
                                      self.height * 32 + 20])
        self._image.blit(self._outline, [0, 0])
        self._image.blit(image, [10, 10])
        self._image.blit(self._chain_spr.image, self._chain_spr.rect)

    def pick_up(self, special):
        self._player.pick_up(special)

    # Remove has to be done by the box itself, but this we can do here...
    def add_box(self, xy, box):
        BasicField.add_box(self, xy, box)
        self._sprites.add(box)

    def move(self, ev):
        if self._disease == REVERSE:
            ev = { LEFT: RIGHT, RIGHT: LEFT, UP: DOWN, DOWN: UP,
                   ROT_CW: ROT_CC, ROT_CC: ROT_CW }.get(ev, ev)

        if self.state == Field.FALLING and self.falling:
            if ev == LEFT: self.falling.go_left()
            elif ev == RIGHT: self.falling.go_right()
            elif ev == DOWN: self.falling.go_down()
            elif ev == ROT_CC: self.falling.rot_cc()
            elif (ev == ROT_CW or
                  (ev == UP and
                   config.getboolean("settings", "rotate_on_up"))):
                  self.falling.rot_cw()

    def _state_falling(self, time):
        if not self.falling:
            if self._field[0][self._insrow] is not None: self._player.die()
            self.falling = self._player.get_next_falling(time)
            self._player.tick()
        self.falling.update(time)
        if self.falling.locked:
            if self.falling.bonus:
                self._player.score.score += 10
            self.speed = max(250, self.speed - 5)
            self.state = Field.FIXING1
            self._ntime = time + 20
            self.falling.deposit()
            self.falling = None

    def _state_fixing1(self, time):
        # Strictly speaking, this loop is overkill, since we know
        # that at most one thing will fall...
        # So, if we need to, optimize this by using the return
        # value of deposit later.
        if time > self._ntime: 
            self._ntime = time + 20
            if not self.fall(): self.state = Field.TICKING

    def _state_ticking(self, time):
        tickers, extickers = self.tick(BoxSprite)
        if len(tickers) != 0: TickBox.sound.play()
        for t in extickers: t.kill()
        self.state = Field.MERGING

    def _state_merging(self, time):
        dead = self.merge()
        for spr in dead: spr.kill()
        if len(dead) == 0: self.state = Field.BREAKING

    def _state_breaking(self, time):
        if self._break_time is None:
            killed_count, dead = self.breaking()
            self._player.score.score +=  killed_count * 100
            self._killed += killed_count * (1 + self._chain / 2.0)
            self._broke_any_last = (len(dead) != 0)
            self._dead = dead
            if len(dead) > 0:
                BreakBox.sound.play()
                self._break_time = time + 100
            else:
                self.state = Field.FIXING2
        elif time > self._break_time:
            for spr in self._dead: spr.kill()
            self._break_time = None
            self.state = Field.FIXING2

    def _state_fixing2(self, time):
        if not self._broke_any_last:
            # Process pending boning drops for other players, and then
            # switch to our own boning state.
            val = int(self._killed)
            self._killed = 0
            self._player.distribute_boning(val)
            self.state = Field.BONING

        # *This* loop is not overkill, since stuff will keep breaking
        # and falling...
        elif time > self._ntime: 
            self._ntime = time + 20
            if not self.fall():
                self._chain += 1
                if self._chain > 1:
                    self.max_chain = max(self.max_chain, self._chain)
                self._chain_spr.chain = self._chain
                self.state = Field.MERGING

    def _state_boning(self, time):
        for x, box in enumerate(self._player.get_boning_row()):
            if box:
                if self._field[0][x] is None:
                    self._field[0][x] = box
                    box.move([x, 0])
                    self._sprites.add(box)
        self.state = Field.BONING2
        self._ntime = time

    def tech_bonus(self):
        self._chain_spr.text = "tech bonus!"
        self._player.score.score += 1000

    def _state_boning2(self, time):
        if time > self._ntime: 
            self._ntime = time + 50
            could_move = self.fall()

            if self._player.is_boned():
                self.state = Field.BONING
            elif not could_move:
                self._chain = 0
                self._chain_spr.chain = self._chain
                self.state = Field.FALLING

    def update(self, time):
        if self._disease != HEALTHY and time > self._disease_end:
            if self._disease == BLINK: self.image.set_alpha(256)
            self._disease = HEALTHY
        self._chain_spr.update(time)
        self._sprites.update(time)
        self._state_calls[self.state](time)
        self._render()

# Display the piece that will be dropped next.
class NextBlock(Sprite):
    def __init__(self, topleft, char):
        Sprite.__init__(self)
        self._base = char.border([42, 110])
        nxt = textfx.shadow("next:", 20)
        self._base.blit(nxt, nxt.get_rect(center = [32, 20]))
        self._end_scramble = 0
        
        self.image = self._base
        self.rect = self.image.get_rect()
        self.rect.topleft = topleft

    def scramble(self): self._end_scramble = 10

    def set_next(self, block):
        self.image = self._base.convert()
        if self._end_scramble > 0:
            block = pygame.Surface([32, 64])
            block.blit(load.block(random.choice(COLORS)), [0, 0])
            block.blit(load.block(random.choice(COLORS)), [0, 32])
            block.set_colorkey(block.get_at([0, 0]))
            self._end_scramble -= 1
        else:
            block = block.image
        self.image.blit(block, [15, 40])

# Display a number in a box with a short title.
class CountSprite(Sprite):
    def __init__(self, topleft, text, char):
        Sprite.__init__(self)
        self._base = char.border([40, 40])
        inc = textfx.shadow(text, 20)
        self._count = 0
        self._base.blit(inc, inc.get_rect(center = [30, 20]))
        self.image = self._base
        self.rect = self.image.get_rect()
        self.rect.topleft = topleft
        self._set_count(0)

    def _get_count(self): return self._count
    def _set_count(self, count):
        self._count = max(0, count)
        self.image = self._base.convert()
        txt = textfx.shadow(str(self._count), 30)
        self.image.blit(txt, txt.get_rect(center = [30, 40]))

    count = property(_get_count, _set_count)

    def reset(self): self._set_count(0)

# Hold the "special" attack graphic a player currently has.
class SpecialHolder(Sprite):
    def __init__(self, topleft, char):
        Sprite.__init__(self)
        self._base = char.border([40, 40])
        text = textfx.shadow("att.:", 20)
        self._special = HEALTHY
        self._base.blit(text, text.get_rect(center = [30, 20]))
        self.image = self._base
        self.rect = self.image.get_rect()
        self.rect.topleft = topleft

    def _get_special(self): return self._special
    def _set_special(self, special):
        if special:
            self.image = self._base.convert()
            self._special = special
            self.image.blit(SpecialSprite.load(self.special), [20, 30])
        else:
            self.image = self._base

    special = property(_get_special, _set_special)

# Display the player's score.
class Score(Sprite):
    def __init__(self, topleft, char):
        Sprite.__init__(self)
        self._base = char.border([120, 40])
        title = textfx.shadow("score:", 20)
        self._score = 0
        self._base.blit(title, title.get_rect(topleft = [15, 10]))
        self.image = self._base
        self.rect = self.image.get_rect()
        self.rect.topleft = topleft
        self.score = 0

    def _get_score(self): return self._score
    def _set_score(self, score):
        self._score = score
        self.image = self._base.convert()
        txt = textfx.shadow("%09d" % self._score, 30)
        self.image.blit(txt, txt.get_rect(midright = [125, 38]))

    score = property(_get_score, _set_score)

class AbstractPlayer(object):
    def __init__(self, pid, char):
        self._pid = pid
        self.char = char
        self.is_ai = False
        self.centerx = self.topleft[0] + 96 + 10
        self.score = Score([self.topleft[0] + 72, self.topleft[1] + 520],
                            self.char)

    def win(self):
        self.score.score += 500 * self.field.max_chain
        self.score.score += 100 * self.field.max_gemsize

    def win_data(self):
        statbox = self.char.border([160, 230])
        oldscore = self.score.score - (500 * self.field.max_chain +
                                       100 * self.field.max_gemsize)
        t1l = textfx.shadow("Score:", 30)
        t1r = textfx.shadow("%d" % oldscore, 26)
        t2l = textfx.shadow("Largest Crystal:", 30)
        t2r = textfx.shadow("%d x 100 = +%d" % (self.field.max_gemsize,
                                          self.field.max_gemsize * 100), 26)
        t3l = textfx.shadow("Longest Chain:", 30)
        t3r = textfx.shadow("%d x 500 = +%d" % (self.field.max_chain,
                                         500 * self.field.max_chain), 26)
        t4l = textfx.shadow("Total Score:", 30)
        t4r = textfx.shadow("%d" % self.score.score, 30)
        statbox.blit(t1l, [15, 15])
        statbox.blit(t2l, [15, 65])
        statbox.blit(t3l, [15, 120])
        statbox.blit(t4l, [15, 185])
        statbox.blit(t1r, [statbox.get_width() - 20 - t1r.get_width(), 40])
        statbox.blit(t2r, [statbox.get_width() - 20 - t2r.get_width(), 90])
        statbox.blit(t3r, [statbox.get_width() - 20 - t3r.get_width(), 150])
        statbox.blit(t4r, [statbox.get_width() - 20 - t4r.get_width(), 210])
        return statbox

    def distribute_boning(self, count): pass

    def get_boning_row(self):
        if len(self._pending_boning) > 0:
            ret = self._pending_boning.pop(0)
            self.drop_count.count -= (len(ret) - ret.count(None))
            return ret
        else: return []

    def die(self):
        print "Player %d is dead!" % (self._pid + 1)
        self.dead = True

    def tick(self): pass

    # Called when a game is started. Players can persist across games.
    def start(self, seed, others):
        self._rand = random.Random(seed)
        self._pending_boning = []
        self.dead = False
        self._gen = BoxGen(self._rand, self.colors,
                                 isinstance(self, SinglePlayer))
        self.others = filter(lambda x: x is not self, others)

        self.dead_image = pygame.Surface([self.field.width * 32,
                                          self.field.height * 32])
        img = load.block("gray")
        for i in range(0, self.dead_image.get_width(), 32):
            for j in range(0, self.dead_image.get_height(), 32):
                self.dead_image.blit(img, [i, j])
        self.dead_image = self.char.border(self.dead_image)

        self._next = FallingBoxes(self._gen.get([-1, -1]),
                                  self._gen.get([-1, -1]),
                                  self.field)
        self._next.rect = self._next.image.get_rect()
        self._next.rect.topleft = [self.topleft[0] + 30, 500]
        self._next_disp = NextBlock([self.topleft[0], self.topleft[1] + 450],
                                    self.char)
        self.sprites = RenderUpdates([self.field,self._next_disp,self.score])
        self._next_disp.set_next(self._next)

    def reset(self):
        self.dead = False

    def get_next_falling(self, time):
        n = self._next
        self._next = FallingBoxes(self._gen.get([-1, -1]),
                                  self._gen.get([-1, -1]),
                                  self.field)
        self._next.rect = self._next.image.get_rect()
        self._next.rect.topleft = [self.topleft[0] + 30, 500]
        self._next_disp.set_next(self._next)
        n.start(time)
        return n

    def is_boned(self): return (len(self._pending_boning) != 0)

    def use_special(self): pass

    def deboning(self, value): abstract
    def enqueue(self, value): abstract

    def update(self, time):
        self.sprites.update(time)

class VersusPlayer(AbstractPlayer):
    def __init__(self, pid, char):
        if pid == 0: self.topleft = [10, 0]
        elif pid == 1: self.topleft = [800 - 32 * 6 - 30, 0]
        self.colors = COLORS[:4]
        AbstractPlayer.__init__(self, pid, char)

    def start(self, seed, others):
        self.field = Field(self)
        self.special = None
        AbstractPlayer.start(self, seed, others)
        self.drop_count = CountSprite([self.topleft[0] + 73,
                                        self.topleft[1] + 450],
                                       "new:", self.char)
        self.sprites.add(self.drop_count)
        if config.getboolean("settings", "combat"):
            self._special_spr = SpecialHolder([self.topleft[0] + 152,
                                               self.topleft[1] + 450],
                                              self.char)
            self.sprites.add(self._special_spr)

    def enqueue(self, rows):
        for row in rows:
            self.drop_count.count += (len(row) - row.count(None))
            # Hacky -- the and acts like a conditional.
            row = [(c and TickBoxSprite(c, [-1, -1])) for c in row]
            self._pending_boning.append(row)

    def distribute_boning(self, value):
        value = (float(self.deboning(value)) / len(self.others))
        if value == 0: return
        for p in self.others:
            v = self.char.drop.multiply(value)
            p.enqueue(v)

    def pick_up(self, special):
        Special.sound.play()
        self._special_spr.special = self.special = special

    def use_special(self):
        if self.special is None: return
        elif self.special == CLEAR:
            self.field.clear()
            self.field._chain_spr.text = Special.names[CLEAR] + "!"
        elif self.special is not None:
            for p in self.others: p.field.inflict(self.special)
        self._special_spr.special = self.special = None
        

    def deboning(self, value):
        if len(self._pending_boning) == 0: return value

        rows = self._pending_boning
        total = sum([len(row) - row.count(None) for row in rows])
        half_time = False
        if value >= total: half_time = True
        while value > 0:
            if len(rows) == 0: break
            for i in range(len(rows[-1])):
                if rows[-1] is not None and value > 0:
                    rows[-1][i] = None
                    value -= 2
                    self.drop_count.count -= 1
            if rows[-1].count(None) == len(rows[-1]): rows.pop()
        if half_time:
            for row in rows:
                for box in row:
                    if isinstance(box, TickBox): box.time_left = 3
        return max(0, value)

class AIPlayer(VersusPlayer):
    AIS = { STUPID: "StupidAI",
            VEASY: "VeryEasyAI",
            EASY: "EasyAI",
            NORMAL: "NormalAI",
            HARD: "HardAI",
            INSANE: "InsaneAI" }
    
    def __init__(self, pid, char, ai_name = None):
        # I, for one, welcome our new robot overlords.
        VersusPlayer.__init__(self, pid, char)
        self.is_ai = True
        import ai
        if ai_name == None:
            ai_name = AIPlayer.AIS[config.getint("settings", "ai")]
        self._ai = ai.__dict__[ai_name](self)

    def start(self, *args):
        VersusPlayer.start(self, *args)
        self._iter = None
        self._goal = None
        self._moved = False
        self._aimove_ntime = 0

    def tick(self):
        self._ai.incoming(self.field, self.field.falling)
        self._iter = iter(self._ai)
        self._goal = None
        self._moved = False

    def update(self, time):
        VersusPlayer.update(self, time)
        if self._iter:
            move = self._iter.next()
            if move != None:
                self._iter = None
                self._goal = move
                self._aimove_ntime = time - 1

        if self._goal and time > self._aimove_ntime and self.field.falling:
            if self._goal[0] != self.field.falling._orient:
                events.post(Event(PLAYER, key = ROT_CC, player = self._pid))
            elif self._goal[1] < self.field.falling.x:
                events.post(Event(PLAYER, key = LEFT, player = self._pid))
            elif self._goal[1] > self.field.falling.x:
                events.post(Event(PLAYER, key = RIGHT, player = self._pid))
            else:
                self._goal = None
                self._moved = True
            self._aimove_ntime = time + self._ai.delta

        if (self._ai.drops and
            self._moved and time > self._aimove_ntime and self.field.falling):
            events.post(Event(PLAYER, key = DOWN, player = self._pid))
            self._aimove_ntime = time + self._ai.drops

class SinglePlayer(AbstractPlayer):
    def __init__(self, pid, char):
        self.topleft = [155, 0]
        self.colors = COLORS
        AbstractPlayer.__init__(self, pid, char)

    def tick(self):
        self.tension.tick()
        if self.tension.turns_left <= 0:
            self.enqueue(self.tension.bone())
        self.ttime.count = self.tension.turns_left
        self.drop_count.count = self.tension.next_boning

    def start(self, seed, others):
        self.field = Field(self, 15, 13)
        AbstractPlayer.start(self, seed, others)
        self.tension = TensionBoner()
        self.drop_count = CountSprite([self.topleft[0] + 73,
                                  self.topleft[1] + 450],
                                 "new:", self.char)
        self.ttime = CountSprite([self.topleft[0] + 150,
                                  self.topleft[1] + 450],
                                 "turns:", self.char)
        self.ttime.count = 10
        self.drop_count.count = 2
        self.sprites.add([self.drop_count, self.ttime])

    def distribute_boning(self, value):
        self.deboning(value)

    def enqueue(self, rows):
        for row in rows:
            # Hacky -- the and acts like a conditional.
            row = [(c and TickBoxSprite(c, [-1, -1])) for c in row]
            self._pending_boning.append(row)

    def deboning(self, value):
        self.tension.debone(self, value)
        self.drop_count.count = self.tension.next_boning
        self.ttime.count = self.tension.turns_left
        return 0

class FightSprite(Sprite):
    sounds = [load.sound("begin.wav")]
    for i in range(1, 10):
        sounds.append(load.sound("round%d.wav" % i))
    for snd in sounds: snd.set_volume(0.6)

    def __init__(self, match, matches):
        Sprite.__init__(self)
        self._start = pygame.time.get_ticks()
        self._played_round = False
        self._played_begin = False
        self._match = match + 1
        text = "Round %d/%d" % (self._match, matches)
        self._later = textfx.shadow("Begin!", 300, color = [255, 255, 255])
        self._later_rect = self._later.get_rect(center = [400, 300])
        self.image = textfx.shadow(text, 150, color = [255, 255, 255])
        self.rect = self.image.get_rect()
        self.rect.right = 0
        self.rect.centery = 300
        self._w = 800 + self.image.get_width()

    def update(self, time):
        if time - self._start < 2000:
            if not self._played_round:
                FightSprite.sounds[self._match].play()
                self._played_round = True
            self.rect.right = int(((time - self._start) / 2000.0) * self._w)
        elif time - self._start < 3000:
            if not self._played_begin:
                FightSprite.sounds[0].play()
                self._played_begin = True
            self.image = self._later
            self.rect = self._later_rect
        else:
            self.kill()

class Game(object):
    def __init__(self):
        self._sprites = RenderUpdates()
        self._screen = pygame.display.get_surface()
        self._em = EventManager()
        self._pickaxe = load.image("pickaxe.png")
        self._light_axe = self._pickaxe.copy()
        alphs = pygame.surfarray.pixels_alpha(self._light_axe)
        for row in alphs:
            for i in range(len(row)): row[i] = row[i] / 2
        del(alphs)

    def play(self, matches, wins):
        seed = pygame.time.get_ticks()
        screen = pygame.display.get_surface()

        for i in range(wins[0]):
            screen.blit(self._pickaxe, [225 + 70 * i, 400])
        for i in range(wins[0], (matches + 1) / 2):
            screen.blit(self._light_axe, [225 + 70 * i, 400])
        for i in range(wins[1]):
            screen.blit(self._pickaxe, [505 - 70 * i, 500])
        for i in range(wins[1], (matches + 1) / 2):
            screen.blit(self._light_axe, [505 - 70 * i, 500])
        pygame.display.update()

        for p in self._players: p.start(seed, self._players)
        em = EventManager()
        quit = False
        paused = False
        dim = pygame.Surface(screen.get_size(), 16)
        dim.set_alpha(128)
        f = pygame.font.Font(None, 48)
        txt = f.render("- paused -", True, [255, 255, 255])
        dim.blit(txt, txt.get_rect(center = [400, 300]))
        start_pause = 0
        prev_screen = None
        events.DELAY = 100
        pygame.key.set_repeat(100, 75)
        while (not quit and
               ((len(self._players) > 1 and
                 [p.dead for p in self._players].count(False) > 1)
                or (len(self._players) == 1 and not self._players[0].dead))):
            for ev in em.get():
                if ev.type == PLAYER:
                    if ev.player < len(self._players):
                        if ev.key == CONFIRM:
                            if pygame.time.paused:
                                pygame.event.post(Event(PAUSE))
                            else:
                                self._players[ev.player].use_special()
                        else:
                            self._players[ev.player].field.move(ev.key)
                elif ev.type == PAUSE:
                    pygame.time.toggle_pause()
                    if pygame.time.paused:
                        prev_screen = screen.convert()
                        screen.blit(dim, [0, 0])
                    else: screen.blit(prev_screen, [0, 0])
                    pygame.display.update()
                elif ev.type == QUIT:
                    quit = True
                    break
            if quit: break

            if not pygame.time.paused:
                for p in self._players:
                    p.update(pygame.time.get_ticks())

                for p in self._players:
                    pygame.display.update(p.sprites.draw(screen))

            pygame.time.clock.tick(60)
        pygame.key.set_repeat(200, 75)
        events.DELAY = 200

    def block_out(self):
        try: pygame.mixer.music.fadeout(1000)
        except: pass
        dead_snd = load.sound("death.wav")
        indices = [i for i, p in enumerate(self._players) if p.dead]
        dead_snd.play()
        t = start = pygame.time.get_ticks()
        while t - start < 1000:
            h = 400 - (400 * ((t - start) / 1000.0))
            self._screen.set_clip([[0, h], [800, 450 - h]])
            for i in indices:
                pygame.display.update(self._screen.blit(
                    self._players[i].dead_image,
                    self._players[i].topleft))
            pygame.time.clock.tick(60)
            t = pygame.time.get_ticks()
        self._screen.set_clip()

    def wait_reset(self, text, char):
        cont = True
        last = pygame.time.get_ticks()
        screen = pygame.display.get_surface()
        #pygame.mixer.music.load(os.path.join("music", "between.ogg"))
        #pygame.mixer.music.set_volume(0.5)
        #pygame.mixer.music.play(-1)
        while cont:
            t = pygame.time.get_ticks()
            for ev in self._em.get():
                if (ev.type == QUIT or
                    (ev.type == PLAYER and
                     (ev.key in [CONFIRM, ROT_CC, ROT_CW]))):
                    cont = False
            if t - last > 80:
                img = text.animate()
                border = char.border(img.get_size())
                border.blit(img, [10, 10])
                r = border.get_rect(center = [400, 100])
                pygame.display.update(screen.blit(border, r))
                last = t
            pygame.time.clock.tick(60)

        for p in self._players: p.reset()
        #pygame.mixer.music.stop()
        #pygame.mixer.music.set_volume(1.0)

class SingleGame(Game):
    def __init__(self):
        Game.__init__(self)
        self._players = [SinglePlayer(0, Character.default)]
        player = self._players[0]
        screen = pygame.display.get_surface()
        bkg = player.char.images["background"]
        try: pygame.mixer.music.fadeout(2000)
        except pygame.error: pass
        wipes.wipe_in(bkg)
        screen.blit(bkg, [0, 0])
        pygame.mixer.music.load(os.path.join("music", "single.ogg"))
        pygame.mixer.music.play(-1)
        player.dead = True
        self.play(0, [0, 0])
        self.block_out()

        text = "Game Over!"
        text = textfx.TextWavey(50, text, [255, 255, 255], amount = 5)

        statbox = player.win_data()
        statbox_r = statbox.get_rect(center = [player.centerx, 300])
        screen.blit(statbox, statbox_r)
        pygame.display.update()

        self.wait_reset(text, player.char)

        sec = "scores-single"
        score = player.score.score
        place = None
        if score > int(config.get(sec, "1").split(",")[1]):
            config.set(sec, "3", config.get(sec, "2"))
            config.set(sec, "2", config.get(sec, "1"))
            place = 1
        elif score > int(config.get(sec, "2").split(",")[1]):
            config.set(sec, "3", config.get(sec, "2"))
            place = 2
        elif score > int(config.get(sec, "3").split(",")[1]):
            place = 3

        if place:
            surf = player.char.border([500, 60])
            surf.blit(textfx.shadow("You got a high score! Enter your name:",
                                    26), [15, 10])
            string = u""
            while True:
                r = screen.blit(surf, [80, 440])
                screen.blit(textfx.shadow(string, 32), [100, 475])
                pygame.display.update(r)
                ev = pygame.event.wait()
                while ev.type != KEYDOWN: ev = pygame.event.wait()
                if ev.key == K_ESCAPE or ev.key == K_RETURN: break
                elif ev.key == K_BACKSPACE: string = string[:-1]
                elif ev.unicode == ",": pass
                elif ev.key < 128: string += ev.unicode

            if string == u"":
                string = os.environ.get("USER", "Ogi")
            config.set(sec, str(place), "%s,%d" % (string, score))
        check_unlock(player)

class VersusGame(Game):
    def __init__(self, chars):
        Game.__init__(self)
        matches = config.getint("settings", "matches")
        wins = [0] * len(chars)
        self._players = [VersusPlayer(i, c) for i,c in enumerate(chars)]
        screen = pygame.display.get_surface()

        for match in range(matches):
            bkg = random.choice([p.char.images["background"] for
                                 p in self._players])
            wipes.wipe_in(bkg)
            screen.blit(bkg, [0, 0])
            pygame.display.update()
            f = FightSprite(match, matches)
            f.add(self._sprites)
            try: pygame.mixer.music.fadeout(2000)
            except pygame.error: pass

            while self._sprites:
                self._sprites.update(pygame.time.get_ticks())
                pygame.display.update(self._sprites.draw(screen))
                self._sprites.clear(screen, bkg)
                pygame.time.clock.tick(60)

            pygame.mixer.music.load(os.path.join("music", "versus-1.ogg"))
            pygame.mixer.music.play(-1)
            self.play(matches, wins)
            if True not in [p.dead for p in self._players]: break
            else:
                self.block_out()

            try:
                winner = self._players[[p.dead
                                        for p in self._players].index(False)]
            except ValueError:
                winner = self._players[-1]
            winner.win()

            wins[winner._pid] += 1
            check_unlock(*self._players)
            if wins[winner._pid] > matches / 2:
                WinScreen(winner, matches)
                break

            text = "%s wins!" % (winner.char.name.split()[0])
            text = textfx.TextWavey(50, text, [255, 255, 255], amount = 5)

            statbox = winner.win_data()
            statbox_r = statbox.get_rect(center = [winner.centerx, 300])
            screen.blit(statbox, statbox_r)
            pygame.display.update()

            self.wait_reset(text, winner.char)

class ArcadeGame(Game):
    def __init__(self, chars):
        Game.__init__(self)
        matches = 3
        player = VersusPlayer(0, chars[0])
        screen = pygame.display.get_surface()

        ais = ["StupidAI", "VeryEasyAI", "EasyAI", "EasyAI",
               "NormalAI", "NormalAI", "HardAI", "InsaneAI"]

        quit = False
        for i, char in enumerate(Character.arcade):
            wins = [0] * len(chars)
            self._players = players = [player, AIPlayer(1, char, ais[i])]
            lost = False

            self._prebattle()

            for match in range(matches):
                bkg = random.choice([p.char.images["background"] for
                                     p in self._players])
                wipes.wipe_in(bkg)
                screen.blit(bkg, [0, 0])
                pygame.display.update()
                f = FightSprite(match, matches)
                f.add(self._sprites)
                try: pygame.mixer.music.fadeout(2000)
                except pygame.error: pass

                while self._sprites:
                    self._sprites.update(pygame.time.get_ticks())
                    pygame.display.update(self._sprites.draw(screen))
                    self._sprites.clear(screen, bkg)
                    pygame.time.clock.tick(60)

                pygame.mixer.music.load(os.path.join("music", "versus-1.ogg"))
                pygame.mixer.music.play(-1)
                self.play(matches, wins)
                if True not in [p.dead for p in self._players]:
                    quit = True
                    break
                else:
                    self.block_out()

                winner = filter(lambda p: not p.dead, self._players)[0]
                winner.win()
                check_unlock(self._players[0])
                wins[winner._pid] += 1
                if wins[winner._pid] > matches / 2:
                    if winner._pid == 0:
                        if i >= 3: config.unlock("cpuversus")
                        if i == 7: winner.score.score += 10000
                        WinScreen(winner, "arcade", to_score = (i == 7))
                    else:
                        WinScreen(winner, "arcade", scorer = self._players[0])
                        lost = True
                    break

                text = "%s wins!" % (winner.char.name.split()[0])
                text = textfx.TextWavey(50, text, [255, 255, 255], amount = 5)

                statbox = winner.win_data()
                statbox_r = statbox.get_rect(center = [winner.centerx, 300])
                screen.blit(statbox, statbox_r)
                pygame.display.update()

                self.wait_reset(text, winner.char)

            if lost or quit: break

    def _prebattle(self):
        screen = pygame.display.get_surface()
        em = EventManager()
        chars = [player.char for player in self._players]

        bkg = Character.default.images["background"].convert()
        bkg.blit(chars[0].border(chars[0].images["portrait"]), [20, 20])
        bkg.blit(chars[1].border(chars[1].images["portrait"]), [580, 390])

        txt1 = textfx.shadow(chars[0].name, 60)
        txt2 = textfx.shadow(chars[1].name, 60)
        bkg.blit(txt1, [230, 30])
        bkg.blit(txt2, txt2.get_rect(bottomright = [560, 580]))

        txt = textfx.shadow("versus", 40)
        bkg.blit(txt, txt.get_rect(center = [400, 300]))

        wipes.wipe_in(bkg)
        screen.blit(bkg, [0, 0])
        pygame.display.update()
        cont = True
        while cont:
            for ev in em.get():
                if (ev.type == QUIT or
                    (ev.type == PLAYER and
                     (ev.key in [CONFIRM, ROT_CC, ROT_CW]))):
                    cont = False
            pygame.time.clock.tick(60)

class AIGame(Game):
    def __init__(self, chars, all_ais = False, ai1 = None, ai2 = None):
        Game.__init__(self)
        matches = config.getint("settings", "matches")
        wins = [0] * len(chars)
        if all_ais:
            self._players = [AIPlayer(0, chars[0], ai1),
                             AIPlayer(1, chars[1], ai2)]
        else:
            self._players = [VersusPlayer(0, chars[0]),
                             AIPlayer(1, chars[1], ai1)]

        for match in range(matches):
            bkg = random.choice([p.char.images["background"] for
                                 p in self._players])
            screen = pygame.display.get_surface()
            wipes.wipe_in(bkg)
            screen.blit(bkg, [0, 0])
            pygame.display.update()
            f = FightSprite(match, matches)
            f.add(self._sprites)
            try: pygame.mixer.music.fadeout(2000)
            except pygame.error: pass

            while self._sprites:
                self._sprites.update(pygame.time.get_ticks())
                pygame.display.update(self._sprites.draw(screen))
                self._sprites.clear(screen, bkg)
                pygame.time.clock.tick(60)

            pygame.mixer.music.load(os.path.join("music", "versus-1.ogg"))
            pygame.mixer.music.play(-1)
            self.play(matches, wins)
            if True not in [p.dead for p in self._players]: break
            else:
                self.block_out()

            winner = self._players[[p.dead
                                    for p in self._players].index(False)]
            winner.win()

            wins[winner._pid] += 1
            if wins[winner._pid] > matches / 2:
                WinScreen(winner, matches, scorer = self._players[0])
                break

            text = "%s wins!" % (winner.char.name.split()[0])
            text = textfx.TextWavey(50, text, [255, 255, 255], amount = 5)

            statbox = winner.win_data()
            statbox_r = statbox.get_rect(center = [winner.centerx, 300])
            screen.blit(statbox, statbox_r)
            pygame.display.update()

            self.wait_reset(text, winner.char)

def WinScreen(winner, score_sec, to_score = True, scorer = None):
    em = EventManager()
    if scorer is None: scorer = winner
    screen = pygame.display.get_surface()
    print "Player %d wins!" % (winner._pid + 1)
    wipes.wipe_out()
    wipes.wipe_in(winner.char.images["background"])
    font = textfx.WrapFont(30, 400)
    text = font.render(random.choice(winner.char.quips))
    box = winner.char.border([text.get_width() + 20, text.get_height() + 20])
    statbox = winner.win_data()
    box.blit(text, [20, 20])
    screen.blit(winner.char.border(winner.char.images["portrait"]), [50, 50])
    screen.blit(box, [50, 350])
    screen.blit(statbox, [350, 50])
    pygame.display.update()

    if winner.is_ai:
        dead = load.sound("gameover.wav")
        dead.set_volume(0.5)
        dead.play()

    cont = True
    while cont:
        for ev in em.wait():
            if (ev.type == QUIT or
                (ev.type == PLAYER and
                 (ev.key in [CONFIRM, ROT_CC, ROT_CW]))):
                cont = False

    score = scorer.score.score
    place = None

    if not scorer.is_ai and to_score:
        sec = "scores-versus-%s" % str(score_sec)
        if score > int(config.get(sec, "1").split(",")[1]):
            config.set(sec, "3", config.get(sec, "2"))
            config.set(sec, "2", config.get(sec, "1"))
            place = 1
        elif score > int(config.get(sec, "2").split(",")[1]):
            config.set(sec, "3", config.get(sec, "2"))
            place = 2
        elif score > int(config.get(sec, "3").split(",")[1]):
            place = 3

    if not scorer.is_ai and to_score and place:
        surf = scorer.char.border([500, 60])
        surf.blit(textfx.shadow("You got a high score! Enter your name:", 26),
                  [15, 10])
        string = u""
        while True:
            r = screen.blit(surf, [80, 440])
            screen.blit(textfx.shadow(string + "_", 32), [100, 475])
            pygame.display.update(r)
            ev = pygame.event.wait()
            while ev.type != KEYDOWN: ev = pygame.event.wait()
            if ev.key == K_ESCAPE or ev.key == K_RETURN: break
            elif ev.key == K_BACKSPACE: string = string[:-1]
            elif ev.unicode == ",": pass
            elif ev.key < 128: string += ev.unicode

        if string == u"":
            string = os.environ.get("USER", scorer.char.name)
        config.set(sec, str(place), "%s,%d" % (string, score))

def check_unlock(*players):
    for p in filter(lambda p: not p.is_ai, players):
        if p.field.max_gemsize >= 25:
            config.unlock("unixbros")
        if p.field.max_chain >= 4:
            config.unlock("combat")
