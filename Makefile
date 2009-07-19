#!/usr/bin/make -f

# Makefile for Angry, Drunken Dwarves.
# $Id: Makefile 319 2006-01-12 21:30:11Z piman $

PREFIX ?= /usr/local

MODULES = ai.py \
          boxes.py \
          characters.py \
          charselect.py \
          config.py \
          constants.py \
          dirstore.py \
          events.py \
          game.py \
          howtoplay.py \
          load.py \
          menu.py \
          pygame_ext.py \
          textfx.py \
          unlocker.py \
          util.py \
          wipes.py

TO = share/games/angrydd

all: check

check:
	@/bin/echo -n "Checking for Python... "
	@which python || ( echo "Not found." && /bin/false )
	@./check.py

install:
	install -d $(DESTDIR)$(PREFIX)/$(TO)/characters
	install -m 755 angrydd.py $(DESTDIR)$(PREFIX)/$(TO)
	install -m 644 $(MODULES) angrydd.png $(DESTDIR)$(PREFIX)/$(TO)
	cp -R music sounds images $(DESTDIR)$(PREFIX)/$(TO)
	cp -R characters/*.dwarf* characters/default $(DESTDIR)$(PREFIX)/$(TO)/characters
	install -d $(DESTDIR)$(PREFIX)/games
	ln -sf ../$(TO)/angrydd.py $(DESTDIR)$(PREFIX)/games/angrydd
	mkdir -p $(DESTDIR)$(PREFIX)/share/man/man6/
	install -m 644 angrydd.6 $(DESTDIR)$(PREFIX)/share/man/man6/angrydd.6

clean:
	rm -f *.pyc

distclean: clean
	rm -f *~ angryddrc \#*
