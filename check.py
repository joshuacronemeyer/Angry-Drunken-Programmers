#!/usr/bin/env python
# check.py -- check for system requirements
# public domain

NAME = "Angry, Drunken Dwarves"

import sys

sys.stdout.write("Checking Python version: ")
sys.stdout.write(".".join(map(str, sys.version_info[:2])) + ".\n")
if sys.version_info < (2, 3):
    raise SystemExit("%s requires at least Python 2.3. (http://www.python.org)" % NAME)

sys.stdout.write("Checking for Pygame: ")
try: import pygame
except ImportError:
    raise SystemExit("Not found.\n%s requires Pygame. (http://www.pygame.org)" % NAME)

print pygame.ver + "."
if pygame.ver < "1.6.2":
    raise SystemExit("%s requires at least Pygame 1.6.2. (http://www.pygame.org)" % NAME)

sys.stdout.write("Checking for pygame.surfarray: ")
try:
  import pygame.surfarray
  print "found."
except (ImportError, NotImplementedError):
  raise SystemExit("not found!\n%s requires the Pygame surfarray module." % NAME)

if pygame.ver == "1.6.2":
    print """\n WARNING:
  Pygame 1.6.2 is supported, but has a buggy line-drawing algorithm.
  Crystals will be drawn incorrectly."""
print "\nYour system meets the requirements to install %s." % NAME
print "Type 'make install' (as root) to install it."
