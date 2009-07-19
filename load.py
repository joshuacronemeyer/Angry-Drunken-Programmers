# load.py -- sound/image loading wrappers for graceful failure
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: load.py 296 2005-10-06 06:36:15Z piman $"

import pygame
import pygame_ext
import math

from dirstore import DirStore
from constants import *

color_cache = {}

HUE_MAP = {
    "red": 0,
    "orange": 25,
    "yellow": 60,
    "green": 120,
    "cyan": 175,
    "blue": 230,
    "purple": 295,
    }

GEM_POLYGON = [
    # the overall shape, so there are no gaps:
    ([1.00, 0.50],
     [[0, 4], [4,0], [28, 0], [32, 4], [32, 28], [28, 32], [4, 32], [4, 28]]),
    # individual facets, top to bottom, right to left:
    # top row
    ([0.20, 0.90], [[0, 4], [4, 0], [16, 0]]),
    ([0.60, 0.70], [[4, 0], [16, 0], [16, 4]]),
    ([0.50, 0.75], [[16, 0], [28, 0], [16, 4]]),
    ([1.00, 0.50], [[0, 4], [4, 0], [16, 4]]),
    # second row
    ([0.55, 0.75], [[0, 4], [4, 4], [4, 16], [0, 16]]),
    ([0.85, 0.55], [[4, 4], [16, 4], [16, 16], [4, 16]]),
    ([1.00, 0.35], [[16, 4], [28, 4], [28, 16], [16, 16]]),
    ([0.75, 0.60], [[28, 4], [32, 4], [32, 16], [28, 16]]),
    # third row
    ([0.85, 0.55], [[0, 16], [4, 16], [4, 28]]),
    ([1.00, 0.25], [[0, 16], [4, 28], [0, 28]]),
    ([1.00, 0.40], [[4, 16], [16, 16], [16, 28], [4, 28]]),
    ([1.00, 0.10], [[16, 16], [28, 16], [28, 28], [16, 28]]),
    ([0.65, 0.70], [[28, 16], [32, 16], [32, 28]]),
    ([0.35, 0.85], [[28, 16], [32, 28], [28, 28]]),
    # bottom row
    ([0.85, 0.60], [[0, 28], [8, 28], [4, 32]]),
    ([1.00, 0.10], [[4, 32], [8, 28], [16, 28], [16, 32]]),
    ([0.65, 0.70], [[16, 28], [28, 32], [16, 32]]),
    ([0.40, 0.80], [[16, 28], [28, 28], [28, 32]]),
    ([0.20, 0.90], [[28, 28], [32, 28], [28, 32]])
    ]

# Load an image of a block of the given color and type. From disk
# if this is the first time loading it; otherwise, from a dict cache.
def block(color, typ = ""):
    if (color, typ) in color_cache:
        return color_cache[(color, typ)].copy()
    else:
        img = image(color + typ + ".png")
        color_cache[(color, typ)] = img.convert()
        return img.copy()

def hsv_to_rgb(h,s,v):
    rgb = []
    if s == 0: rgb = [v, v, v] # grayscale
    elif v == 1: rgb = [1, 1, 1] # white
    elif v == 0: rgb = [0, 0, 0] # black
    else:
	h = h / 60.0
	i = math.floor(h)
	f = h - i
	p = v * (1 - s)
	q = v * (1 - s * f)
	t = v * (1 - s * (1 - f))
	if   i == 0: rgb = [v, t, p]
	elif i == 1: rgb = [q, v, p]
	elif i == 2: rgb = [p, v, t]
	elif i == 3: rgb = [p, q, v]
	elif i == 4: rgb = [t, p, v]
	else: rgb = [v, p, q]
    for i in range(3):
	rgb[i] = int(rgb[i] * 255)
    return rgb

def gem(color, w, h):
    if (color, w, h) in color_cache:
        return color_cache[(color, w, h)].copy()

    if color == "gray": hue = 0
    else: hue = HUE_MAP[color]

    surf = pygame.Surface([w * 32, h * 32], 0, 32)
    for entry in GEM_POLYGON:
        if color == "gray": col = hsv_to_rgb(hue, 0, entry[0][1])
        else: col = hsv_to_rgb(hue, entry[0][0], entry[0][1])
	points = []
	if (w == 1 and h == 1):
	    points = entry[1]
	else:
	    for point in entry[1]:
		points += [[point[0] * w, point[1] * h]]
        pygame.draw.polygon(surf, col, points)
        pygame.draw.aalines(surf, col, True, points, True)
    surf = surf.convert()
    surf.set_colorkey(surf.get_at([0, 0]))
    color_cache[(color, w, h)] = surf.copy()
    return surf

# Load a sound. pygame_ext makes this into a fake object if necessary.
def sound(filename):
    path = os.path.join(angrydd_path, "sounds")
    if os.path.exists(path + ".zip"): store = DirStore(path + ".zip")
    else: store = DirStore(path)
    try: return pygame.mixer.Sound(store.open(filename))
    except ValueError, s:
        #print "W: Unable to load %s: %s" % (filename, s)
        return pygame_ext.FakeSound()
# Load an image, or exit gracefully if it fails.
def image(filename):
    path = os.path.join(angrydd_path, "images")
    if os.path.exists(path + ".zip"): store = DirStore(path + ".zip")
    else: store = DirStore(path)

    try: return pygame.image.load(store.open(filename))
    except pygame.error:
        raise SystemExit("E: Unable to load %s %s" % (filename, err))
