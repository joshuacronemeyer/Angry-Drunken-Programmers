# util.py -- utility fuctions/classes for angrydd
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: util.py 286 2004-09-04 03:51:59Z piman $"

import pygame

# Implement the singleton pattern. Requires Python 2.3.
# In reality this didn't work like I thought, because in Python
# __new__ doesn't call __init__.
class Singleton(object):
    def __new__(*args):
        if not hasattr(args[0], "_singleton"):
            return super(Singleton, args[0]).__new__(*args)
        else: return args[0]._singleton

    def __init__(self):
        type(self)._singleton = self

# "Flatten" a list
def flatten(sequence, is_scalar = lambda x: not isinstance(x, list)):
    result = []
    for item in sequence:
        if is_scalar(item): result.append(item)
        else: result.extend(flatten(item))
    return result

# Regular pygame.time.Clock uses pygame.time.delay; this uses time.wait.
# That way, we save CPU time on Unix.
class WaitClock(object):
    def __init__(self, time_func = pygame.time.get_ticks):
        self._time = time_func
        self._last_tick = 0

    def tick(self, fps = 60):
        t = self._time()
        sleep = (1000 / fps) - (t - self._last_tick)
        self._last_tick = t
        if sleep > 0: pygame.time.wait(sleep)
