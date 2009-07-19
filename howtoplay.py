# howtoplay.py -- a basic help screen for angrydd
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
# Released under the terms of the GNU GPL v2.
__revision__ = "$Id: howtoplay.py 286 2004-09-04 03:51:59Z piman $"

import pygame; from pygame import transform
import characters; from characters import Character

import config
import textfx
import wipes
import load

from events import EventManager
from boxes import SpecialSprite

from constants import *

# Display the "how to play" screen (with appropriate unlocks enabled).
# FIXME: This is pretty messy; the text belongs in a data file rather
# than inline.
def init(*args):
    em = EventManager()
    screen = pygame.display.get_surface()
    move_snd = load.sound("select-move.wav")

    index = 0

    # The format is up to three paragraphs per screen, displayed
    # left, right, left,
    texts = [
        ["In Angry, Drunken Dwarves, you are an angry, drunken dwarf. Why "
         "are you so angry? Who knows. But you've decided to take your "
         "aggression out on other dwarves, by dropping gems on their "
         "heads.",
         "Multicolored gems will fall from the top of the screen. You "
         "should try to arrange them into groups by color. The arrow keys "
         "or a/d and j/l will move them left and right. s or k will make "
         "then fall faster, and q/e and u/o will rotate them.",
         "As gems reach the bottom, they will land and sit in place. If you "
         "put enough gems of the same color in a rectangle shape, they will "
         "merge and form a crystal."
         ],
        ["Less common are break gems. When you drop a break gem on a gem "
         "or crystal of the same color, it will destroy any gems of that "
         "color adjacent to it. Crystals are worth much more than an equal "
         "number of regular gems.",
         "When you destroy gems on your side, it will drop counter gems "
         "onto your opponent. These are harder to destroy, but turn into "
         "regular gems after a few turns. You can try to cancel an incoming "
         "attack by breaking gems yourself, but you'll need to break twice "
         "as many as are coming.",
         "Rarer is the diamond. When you drop a diamond onto something, "
         "it will destroy all gems of that color on your side, even "
         "counter gems! Be careful though, because a crystal "
         "destroyed by a diamond isn't worth any more than normal gems."
         ],
        ["Each dwarf has a drop gem pattern, and an attack strength. The drop "
         "pattern is a display of what kinds of gems will be dropped when "
         "you attack your opponent. Small attacks will drop the same "
         "row over and over, which will probably help them!",
         "The attack strength is a measurement of how strong your drop "
         "pattern is; drops with weirder patterns are harder to plan "
         "against. Before gems are dropped, they are multiplied by this "
         "attack strength, and so the damage is scaled up or down.",
         "For the most devestating results, try chaining attacks together, "
         "so breaking some gems results in even more breaking afterwards. "
         "Breaking many crystals in a chain can result in huge drops."
         ]
        ]

    drop = pygame.Surface([64, 64])
    drop.blit(load.block("blue"), [0, 0])
    drop.blit(load.block("yellow"), [0, 32])
    drop.blit(load.block("green"), [32, 0])
    drop.blit(load.block("red"), [32, 32])

    crystal = load.gem("green", 4, 3)

    breaks = pygame.Surface([64, 64])
    breaks.blit(load.block("red", "-crash"), [0, 0])
    breaks.blit(load.block("green", "-crash"), [0, 32])
    breaks.blit(load.block("yellow", "-crash"), [32, 0])
    breaks.blit(load.block("blue", "-crash"), [32, 32])

    counters = pygame.Surface([64, 64])
    counters.blit(textfx.lettered_box("5", "green"), [0, 0])
    counters.blit(textfx.lettered_box("4", "blue"), [32, 0])
    counters.blit(textfx.lettered_box("3", "red"), [0, 32])
    counters.blit(textfx.lettered_box("2", "yellow"), [32, 32])

    chain = pygame.Surface([64, 96])
    chain.blit(load.block("blue", "-crash"), [0, 64])
    chain.blit(load.block("green"), [32, 64])
    chain.blit(load.block("green", "-crash"), [32, 32])
    chain.blit(load.block("blue"), [32, 0])

    # Followed by up to three images per screen, right, left, right.
    images = [
        [None, drop, crystal],
        [breaks, counters, load.block("diamond")],
        [Character.arcade[4].drop.render(), None, chain],
        ]

    if config.getboolean("unlock", "single"):
        texts.append([
            "In single player mode, rather than competing against someone "
            "else, you're racing the clock. You have to clear a certain "
            "number of blocks in a certain number of turns, or the ones "
            "left get dumped on you.",
            "Your field is also twice as big. So it sounds easy, right? "
            "Well, to start with, you've got three new colors of gems to "
            "contend with: orange, purple, and cyan.",
            "If that wasn't bad enough, the number of gems you have to clear "
            "goes up much faster than the number of turns you have "
            "to do it, so build up those crystals early and save them."
            ])

        newcols = pygame.Surface([64, 64])
        newcols.blit(load.block("orange"), [16, 0])
        newcols.blit(load.block("cyan"), [0, 32])
        newcols.blit(load.block("purple"), [32, 32])

        
        counts = pygame.Surface([130, 100])
        box = Character.default.border([40, 40])
        text1 = textfx.shadow("new:", 20)
        text2 = textfx.shadow("turns:", 20)
        num1 = textfx.shadow("122", 30)
        num2 = textfx.shadow("10", 30)
        counts.blit(box, [0, 20])
        counts.blit(box, [70, 20])
        counts.blit(text1, text1.get_rect(center = [30, 38]))
        counts.blit(text2, text2.get_rect(center = [100, 38]))
        counts.blit(num1, [12, 45])
        counts.blit(num2, [87, 45])
        images.append([None, newcols, counts])

    if config.getboolean("unlock", "combat"):
        texts.append([
            "Combat blocks look like normal gems with a special symbol "
            "in the middle. These gems don't form crystals, but otherwise "
            "break like normal colored gems. When you break one of these, "
            "you 'pick up' the special attack in it.",
            "To use the attack, press start (enter/2). There are five basic "
            "attacks; from left to right: make your opponent's field blink, "
            "clear  your own field of all blocks,",
            "flip your opponent's screen upside down, disable the 'next' "
            "indicator, drop some gray blocks, or reverse your opponent's "
            "controls. Blink, flip, and reverse last for a few "
            "seconds. Scramble lasts 10 turns."])

        blink = load.block("blue")
        clear = load.block("red")
        rev = load.block("yellow")
        flip = load.block("green")
        gray = load.block("red")
        scram = load.block("purple")
        blink.blit(SpecialSprite.load(BLINK), [6, 6])
        flip.blit(SpecialSprite.load(FLIP), [6, 6])
        clear.blit(SpecialSprite.load(CLEAR), [6, 6])
        rev.blit(SpecialSprite.load(REVERSE), [6, 6])
        gray.blit(SpecialSprite.load(GRAY), [6, 6])
        scram.blit(SpecialSprite.load(SCRAMBLE), [6, 6])
        img1 = pygame.Surface([64, 32])
        img2 = pygame.Surface([64, 64])
        img1.blit(blink, [0, 0])
        img1.blit(clear, [32, 0])
        img2.blit(flip, [0, 0])
        img2.blit(scram, [32, 0])
        img2.blit(gray, [0, 32])
        img2.blit(rev, [32, 32])

        images.append([None, img1, img2])

    wipes.wipe_in(render_help_page(texts[index], images[index]))

    cont = True
    screen.blit(render_help_page(texts[index], images[index]), [0, 0])
    img = textfx.shadow("Enter: Menu - Left/Right: Turn Page (%d/%d)" %
                 (index + 1, len(images)), 18)
    screen.blit(img, [785 - img.get_width(), 10])
    pygame.display.update()
    while cont:
        oldindex = index
        for ev in em.wait():
            if ev.type == QUIT: cont = False
            elif ev.type == PLAYER:
                if ev.key == CONFIRM: cont = False
                elif ev.key == UP or ev.key == LEFT:
                    index = (index - 1) % len(texts)
                    move_snd.play()
                elif ev.key in [DOWN, RIGHT, ROT_CC, ROT_CW]:
                    index = (index + 1) % len(texts)
                    move_snd.play()

        if oldindex != index:
            screen.blit(render_help_page(texts[index], images[index]), [0, 0])
            img = textfx.shadow("Enter: Menu - Left/Right: Turn Page (%d/%d)" %
                         (index + 1, len(images)), 18)
            screen.blit(img, [785 - img.get_width(), 10])
            pygame.display.update()

    return True

# Render a page in the format used above.
def render_help_page(texts, images):
    surf = Character.default.border([780, 580])
    font = textfx.WrapFont(32, 450)

    for i in range(len(texts)):
        text = font.render(texts[i])
        image = images[i]
        if image:
            ri = image.get_rect()
            image.set_colorkey(image.get_at([0, 0]))
        rt = text.get_rect()
        if i & 1:
            if image: ri.centerx = 200
            rt.centerx = 500
        else:
            rt.centerx = 300
            if image: ri.centerx = 630

        if image: ri.centery = 95 + (200 * i)
        rt.centery = 95 + (200 * i)
        surf.blit(text, rt)
        if image: surf.blit(image, ri)
    return surf
