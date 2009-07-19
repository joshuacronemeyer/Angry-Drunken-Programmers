# ai.py -- AI and helper routines for Angry, Drunken Dwarves
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: ai.py 286 2004-09-04 03:51:59Z piman $"

# Trick borrowed from Peter Norvig's Python IAQ:
# http://www.norvig.com/python-iaq.html
def _abstract():
    import inspect
    caller = inspect.getouterframes(inspect.currentframe())[1][3]
    raise NotImplementedError(caller + ' must be implemented in subclass')

import random, math

import util
from game import BasicField
from boxes import TickBox, BreakBox, Box, Special, Diamond

def copy_box(box):
    args = [box.color, [box.x, box.y]]
    newbox = None
    if isinstance(box, Box):
        newbox = Box(*args)
    elif isinstance(box, TickBox):
        newbox = TickBox(*args)
        newbox.time_left = box.time_left
    elif isinstance(box, BreakBox):
        newbox = BreakBox(*args)
    elif isinstance(box, Special):
        newbox = Special(box.color, [box.x, box.y], box.special)
    elif isinstance(box, Diamond):
        newbox = Diamond(box.color, [box.x, box.y])
    return newbox

class AIField(BasicField):
    def __init__(self, field):
        BasicField.__init__(self, field.width, field.height)
        for y, row in enumerate(field):
            for x, box in enumerate(row):
                if field[y][x] is not None:
                    # Only add a box if we're at its topleft, i.e.
                    # don't add merged boxes many times.
                    newbox = copy_box(box)
                    if isinstance(newbox, Box):
                        if box.x != x or box.y != y: continue
                        else: newbox.set_size(box.size, self)
                    if newbox:
                        self.add_box([newbox.x, newbox.y], newbox)

    # Take a turn (move all pieces down, tick, merge, break, repeat)
    # Doesn't do boning. Returns the value of gems broken.
    def take_turn(self):
        while self.fall(): pass
        self.tick()
        while self.merge(): pass
        value, dead = self.breaking()
        while len(dead) > 0:
            while self.fall(): pass
            while self.merge(): pass
            newv, dead = self.breaking()
            value += newv
        return value

    def can_drop1(self, col):
        return (self._field[0][col] is None)

    # Orientation is as described in FallingBoxes#_render.
    def can_drop(self, col, orientation):
        if col >= self.width: return False
        elif orientation == 0: # 2 above 1
            return (self._field[0][col] is None)
        elif orientation == 1:
            return ((col != 0) and self._field[0][col] is None and
                    self._field[0][col - 1] is None)
        elif orientation == 2:
            return (self._field[0][col] is None and
                    self._field[1][col] is None)
        elif orientation == 3:
            return (col != self.width - 1 and
                    self._field[0][col] is None and
                    self._field[0][col + 1] is None)
        else: return False

    # Drop box1 and box2 in the given orientation at the top of this
    # field. Return True (and does it if it thinks such a thing is
    # possible, False otherwise. Possibility is currently only
    # decided by space available at the top, and not any intervening
    # blocks that might block it (i.e. naively)
    def drop(self, boxes, col, orientation):
        box1, box2 = boxes
        if not self.can_drop(col, orientation): return False
        
        elif orientation == 0: # 2 above 1
            if self._field[1][col] is not None:
                self.add_box([col, 0], box1)
            else:
                self.add_box([col, 1], box1)
                self.add_box([col, 0], box2)

        elif orientation == 1: # 2 left of 1
            self.add_box([col, 0], box1)
            self.add_box([col - 1, 0], box2)

        elif orientation == 2: # 2 below 1
            self.add_box([col, 0], box1)
            self.add_box([col, 1], box2)

        elif orientation == 3: # 2 right of 1
            self.add_box([col, 0], box1)
            self.add_box([col + 1, 0], box2)

        return True

    def drop1(self, box, col):
        if not self.can_drop1(col): return False
        else:
            self.add_box([col, 0], box)
            return True

    def get_height(self, col):
        for y in range(self.height):
            if self._field[y][col] != None: return self.height - y
        else: return 0

    def max_height(self):
        return max([self.get_height(i) for i in range(self.width)])

    def average_height(self):
        s = 4 * self.get_height(3) # This is very bad to fill up
        s += sum([self.get_height(x) for x in range(self.width)])
        return s / self.width

    def stddev_height(self):
        avg = self.average_height()
        std_dev = 0
        for i in range(self.width):
            v = avg - self.get_height(i)
            std_dev += v * v
        std_dev /= float(self.width)
        return math.sqrt(std_dev)

    # Expand given only one box; total states = field.width.
    def expand1(self, box, rand = True):
        columns = range(self.width)
        if rand: random.shuffle(columns)

        for col in columns:
            if self.can_drop1(col):
                f = AIField(self)
                newbox = copy_box(box)
                f.drop1(newbox, col)
                yield 0, col, f, [newbox]

    # Expand the state space based on the boxes given. 4 orientations,
    # width of 6 = 22 expansions (after illegal ones removed).
    def expand(self, boxes, rand = True):
        orientations = range(4)
        columns = range(self.width)
        if rand:
            random.shuffle(orientations)
            random.shuffle(columns)
            columns.remove(3); columns.append(3)

        for orientation in orientations:
            for col in columns:
                if self.can_drop(col, orientation):
                    f = AIField(self)
                    newboxes = [copy_box(b) for b in boxes]
                    f.drop(newboxes, col, orientation)
                    yield orientation, col, f, newboxes

class AI(object):
    def __init__(self, player):
        self.player = player
        self.insane = False
        self.drops = 70
        self.delta = 120

    # Expand and find the highest value for the given callback; it
    # defaults to the value of the gems broken if no callback is
    # passed in.
    def find_high(self, h = (lambda *args: args[1])):
        best_score = None
        best_move = (0, 0)
        for orient, col, field, boxes in self.field.expand(self.falling):
            fscore = field.take_turn()
            score = h(orient, col, field, boxes, fscore)
            if best_score is None or score > best_score:
                best_score = score
                best_move = (orient, col)
            yield None
        yield best_move
        return

    # Expand and find the lowest value for the given callback; if
    # the value is 0, it returns it and doesn't expand anymore.
    def find_low(self, h, halt_on_zero = True):
        best_score = None
        best_move = (0, 0)
        for orient, col, field, boxes in self.field.expand(self.falling):
            fscore = field.take_turn()
            score = h(orient, col, field, boxes, fscore)
            if best_score is None or score < best_score:
                best_score = score
                best_move = (orient, col)
            if best_score == 0 and halt_on_zero: break
            yield None
        yield best_move
        return

    def incoming(self, field, falling):
        self.field = AIField(field)
        self.falling = [falling._box1, falling._box2]

    def __iter__(self):
        # Override this function to change how the AI moves. It should
        # return an iterator (or generator) that returns either None
        # when it's still thinking, or a tuple (orientation, column)
        # to put the piece in when it's done. This function is called
        # when a new piece is put into play, and after a move is made
        # is not called again until another piece is put in. (i.e.
        # you can't change your mind.)

        # Note that once your moves are committed, each left/right/rotate
        # motion will take a (nontrivial) fraction of a second! Around
        # 1/12th of a second per move. So, thinking fast is important.

        # Look at the RandomAI for a trivial example.
        _abstract()

class SlowAI(AI):
    def __init__(self, *args):
        AI.__init__(self, *args)
        self.drops = 0
        self.delta = 500

class MediumAI(AI):
    def __init__(self, *args):
        AI.__init__(self, *args)
        self.drops = 100
        self.delta = 150

class FastAI(AI):
    def __init__(self, *args):
        AI.__init__(self, *args)
        self.drops = 80
        self.delta = 100

class SuperFastAI(AI):
    def __init__(self, *args):
        AI.__init__(self, *args)
        self.drops = 25
        self.delta = 25

# A test AI that plays totally randomly.
class RandomAI(AI):
    def __iter__(self):
        yield None
        yield (random.randrange(0, 4),
               random.randrange(0, self.player.field.width))

# Another test AI, just tries to keep average field height low
class KeepLowAI(AI):
    def __iter__(self):
        return self.find_low(self._total_height)

    def _total_height(self, orient, col, field, boxes, score):
        return sum([field.get_height(x) for x in range(field.width)])

class GoodAI(AI):
    def __iter__(self):
        if self.field.get_height(3) > 8:
            return self.find_low(self._emergency)
        elif self.field.max_height() > 9:
            return self.find_high(self._lower_max)
        elif self.field.average_height() < 7:
            return self.find_high(self._form_boxes)
        else:
            return self.find_high()

    def _emergency(self, orient, col, field, boxes, score):
        return (score > 25, field.get_height(3), score)

    def _lower_max(self, orient, col, field, boxes, score):
        return (
            score > 25,
            -field.max_height(),
            score,
            self._gemsize(field))

    def _form_boxes(self, orient, col, field, boxes, score):
        return (
            score > 25,
            field.max_height() < 10,
            self._gemsize(field),
            self._adjacencies(field, boxes))

    def _adjacencies(self, field, boxes):
        adj = 0
        for box in filter(None, boxes):
            if not box.crashed:
                for adjbox in filter(None, box.adjacent(field)):
                    if adjbox.color == box.color: adj += 3
                    else: adj -= 1
        return adj

    def _gemsize(self, field):
        return max([1] + [box.size[0] * box.size[1]
                          for box in util.flatten(field)
                          if box])

class StupidAI(RandomAI, SlowAI): pass
class VeryEasyAI(KeepLowAI, SlowAI): pass
class EasyAI(KeepLowAI, MediumAI): pass
class NormalAI(GoodAI, MediumAI): pass
class HardAI(GoodAI, FastAI): pass
class InsaneAI(GoodAI, SuperFastAI): pass
