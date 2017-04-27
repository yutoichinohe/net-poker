# -*- coding: utf-8 -*-
#!/usr/bin/env python

import sys, os, math, commands
import random, itertools
import numpy as np

#### Constant

Emoji = False

#        s  h  d  c
Suits = (0, 1, 2, 3)
#         A   K   Q  J  T  9  8  7  6  5  4  3  2
Ranks = (12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0)

##
HighCards     = 0
OnePair       = 1
TwoPair       = 2
ThreeOfAKind  = 3
Straight      = 4
Flush         = 5
FullHouse     = 6
FourOfAKind   = 7
StraightFlush = 8

#### Class, Function

class Deck:
    def __init__(self):
        self.cards = [(r,s) for s in Suits for r in Ranks]
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def draw_top(self, n):
        return [self.cards.pop() for i in xrange(n)]

    def draw_card(self, r, s):
        self.cards.remove((r,s))
        return (r,s)

    def draw_card(self, h):
        self.cards.remove(h)
        return h



def poker_hand_rank(list5):
    s = list5
    s.sort()
    n = [x[0] for x in s]

    if n[4] == n[3]:
        if n[4] == n[2]:
            if n[4] == n[1]:
                return s, FourOfAKind
            elif n[1] == n[0]:
                return s, FullHouse
            else:
                return s, ThreeOfAKind
        else:
            if n[2] == n[1]:
                if n[2] == n[0]:
                    return [s[3],s[4],s[0],s[1],s[2]], FullHouse
                else:
                    return s, TwoPair
            elif n[1] == n[0]:
                return [s[2],s[0],s[1],s[3],s[4]], TwoPair
            else:
                return s, OnePair
    else:
        if n[3] == n[2]:
            if n[3] == n[1]:
                if n[3] == n[0]:
                    return [s[4],s[0],s[1],s[2],s[3]], FourOfAKind
                else:
                    return [s[0],s[4],s[1],s[2],s[3]], ThreeOfAKind
            elif n[1] == n[0]:
                return [s[4],s[0],s[1],s[2],s[3]], TwoPair
            else:
                return [s[0],s[1],s[4],s[2],s[3]], OnePair
        else:
            if n[2] == n[1]:
                if n[1] == n[0]:
                    return [s[3],s[4],s[0],s[1],s[2]], ThreeOfAKind
                else:
                    return [s[0],s[3],s[4],s[1],s[2]], OnePair
            elif n[1] == n[0]:
                return [s[2],s[3],s[4],s[0],s[1]], OnePair
            else:
                if s[4][0]-s[0][0] == 4:
                    if s[0][1] == s[1][1] == s[2][1] == s[3][1] == s[4][1]:
                        return s, StraightFlush
                    else:
                        return s, Straight
                elif s[3][0] == 3 and s[4][0] == 12:
                    if s[0][1] == s[1][1] == s[2][1] == s[3][1] == s[4][1]:
                        return [s[4],s[0],s[1],s[2],s[3]], StraightFlush
                    else:
                        return [s[4],s[0],s[1],s[2],s[3]], Straight
                else:
                    if s[0][1] == s[1][1] == s[2][1] == s[3][1] == s[4][1]:
                        return s, Flush
                    else:
                        return s, HighCards



def heads_up(_h1,_h2):
    h1,r1 = _h1
    h2,r2 = _h2

    if r1 > r2:
        return 1
    elif r1 < r2:
        return -1
    else:
        if h1[4][0] > h2[4][0]:
            return 1
        elif h1[4][0] < h2[4][0]:
            return -1
        elif h1[3][0] > h2[3][0]:
            return 1
        elif h1[3][0] < h2[3][0]:
            return -1
        elif h1[2][0] > h2[2][0]:
            return 1
        elif h1[2][0] < h2[2][0]:
            return -1
        elif h1[1][0] > h2[1][0]:
            return 1
        elif h1[1][0] < h2[1][0]:
            return -1
        elif h1[0][0] > h2[0][0]:
            return 1
        elif h1[0][0] < h2[0][0]:
            return -1
        else:
            return 0



def best_hand(h,b):
    a=h+b

    l=len(a)
    if l == 5:
        return poker_hand_rank(a)
    elif l == 6 or l == 7:
        tmp = [list(x) for x in itertools.combinations(a,5)]
        best = poker_hand_rank(tmp[0])
        for i in xrange(1,len(tmp)):
            tmpvs = poker_hand_rank(tmp[i])
            if heads_up(best,tmpvs) != 1:
                best = tmpvs

        return best
    else:
        raise 'invalid card number'



def hand_to_str(h):
    a = [card_to_str(x) for x in h]
    return ' '.join(a)



def handrank_to_str(r):
    if r == HighCards:
        return 'HighCards'
    elif r == OnePair:
        return 'OnePair'
    elif r == TwoPair:
        return 'TwoPair'
    elif r == ThreeOfAKind:
        return 'ThreeOfAKind'
    elif r == Straight:
        return 'Straight'
    elif r == Flush:
        return 'Flush'
    elif r == FullHouse:
        return 'FullHouse'
    elif r == FourOfAKind:
        return 'FourOfAKind'
    elif r == StraightFlush:
        return 'StraightFlush'



def card_to_str(c):
    tmp = ''

    r,s = c

    if r == 12:
        tmp += 'A'
    elif r == 11:
        tmp += 'K'
    elif r == 10:
        tmp += 'Q'
    elif r == 9:
        tmp += 'J'
    elif r == 8:
        tmp += 'T'
    else:
        tmp += '%d'%(r+2)

    if Emoji:
        if s == 0:
            tmp += '♠️ '
        elif s == 1:
            tmp += '❤️ '
        elif s == 2:
            tmp += '♦️ '
        elif s == 3:
            tmp += '♣️ '
    else:
        if s == 0:
            tmp += 's'
        elif s == 1:
            tmp += 'h'
        elif s == 2:
            tmp += 'd'
        elif s == 3:
            tmp += 'c'

    return tmp
