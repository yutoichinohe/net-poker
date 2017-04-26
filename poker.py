#!/usr/bin/env python

import sys, os, math, commands
import random, itertools
import numpy as np
from datetime import datetime

import poker_util as pu

#### Constant

ActionHistoryLength = 1024

## Stage

Deal    = 1
Preflop = 2
Flop    = 3
Turn    = 4
River   = 5

## Available actions

Fold  = 1
Check = 2
Call  = 3
Bet   = 4
Raise = 5
# Allin = 6

## Stage done
StageEnd = 1
AllFold  = 2
ShowDown = 3


#### Class, Function

class Player:
    def __init__(self,name='',stack=0,hand=[]):
        self.name   = name
        self.stack  = stack
        self.hand   = hand
        self.best_hand = []
        self.folded = False
        # self.allin = False
        self.available_actions = []
        self.at_least_one_action = False


class Game:

    def __init__(self,nplayers,init_stack=500,blinds=(1,2,0)):
        if nplayers > 23:
            raise RuntimeError, 'too many players'
        else:
            self.nplayers = nplayers

        self.players = []
        self.zerobets = []
        for i in xrange(nplayers):
            self.players.append(Player(stack=init_stack))
            self.zerobets.append(0)

        self.minimum_bet   = 0
        self.minimum_raise = 0
        self.set_blinds(blinds)

        self.button = 0
        self.action_history = []
        self.reset()



    def reset(self):
        self.bets           = []
        self.pot            = 0
        self.current_pot    = 0

        self.stage          = Deal

        self.current_player = 0

        self.flop           = []
        self.turn           = []
        self.river          = []
        self.board          = []

        self.winners        = []
        self.best_hands     = []


    def prepare(self):
        self.reset()
        self.button = (self.button+1)%self.nplayers

        d = pu.Deck()
        for i in xrange(self.nplayers):
            self.players[i].hand = d.draw_top(2)
            self.players[i].best_hand = []
            self.players[i].folded = False
            # self.players[i].allin = False
            self.players[i].available_actions = []
            self.players[i].at_least_one_action = False


        self.clear_bets()

        self.flop  = d.draw_top(3)
        self.turn  = d.draw_top(1)
        self.river = d.draw_top(1)

        if self.nplayers == 2:
            self.sb = self.button
            self.bb = (self.sb+1)%self.nplayers
        else:
            self.sb = (self.button+1)%self.nplayers
            self.bb = (self.sb+1)%self.nplayers

        [self.a_bet(x,self.blinds[2],ante=True) for x in xrange(self.nplayers)]
        self.proceed()
        self.update_available_actions()
        self.reset_at_least_one_action()
        self.action_history_update('\n    New game : %s to act'%self.players[self.current_player].name)


    def proceed(self):
        if self.stage == Deal:
            self.reset_minimum()
            self.collect_pot()
            self.stage = Preflop
            self.next_player(candidate=(self.sb+2)%self.nplayers)
            self.a_bet(self.sb,self.blinds[0],ante=True)
            self.a_bet(self.bb,self.blinds[1],ante=True)
            self.update_available_actions()
            self.reset_at_least_one_action()

        elif self.stage == Preflop:
            self.reset_minimum()
            self.collect_pot()
            self.stage = Flop
            self.next_player(candidate=(self.button+1)%self.nplayers)
            self.board = self.board + self.flop
            self.update_available_actions()
            self.reset_at_least_one_action()

        elif self.stage == Flop:
            self.reset_minimum()
            self.collect_pot()
            self.stage = Turn
            self.next_player(candidate=(self.button+1)%self.nplayers)
            self.board = self.board + self.turn
            self.update_available_actions()
            self.reset_at_least_one_action()

        elif self.stage == Turn:
            self.reset_minimum()
            self.collect_pot()
            self.stage = River
            self.next_player(candidate=(self.button+1)%self.nplayers)
            self.board = self.board + self.river
            self.update_available_actions()
            self.reset_at_least_one_action()


    def showdown(self):
        best_hands = []
        for x in self.players:
            if not x.folded:
                best_hands.append(pu.best_hand(x.hand,self.board))
                x.best_hand = pu.best_hand(x.hand,self.board)
            else:
                best_hands.append(([],-1))
                x.best_hand = ([],-1)

        current_best = [0]
        current_best_hand = [best_hands[0]]
        for ii in xrange(len(best_hands)-1):
            i = ii+1
            headsup = pu.heads_up(current_best_hand[0],best_hands[i])
            if headsup == 1:
                pass
            elif headsup == 0:
                current_best.append(i)
                current_best_hand.append(best_hands[i])
            else:
                current_best = [i]
                current_best_hand = [best_hands[i]]

        self.winners = current_best
        self.best_hands = current_best_hand


    def set_blinds(self,blinds):
        self.blinds = blinds
        self.minimum_bet = blinds[1]


    def set_stack(self,player,stack):
        self.players[player].stack = stack


    def update_available_actions(self):
        if max(self.bets) == 0:
            for x in self.players:
                x.available_actions = [Fold,Check,Bet]

        elif self.stage == Preflop and max(self.bets) == self.blinds[1]:
            for x in self.players:
                x.available_actions = [Fold,Call,Raise]

            self.players[self.bb].available_actions = [Fold,Check,Raise]

        else:
            for x in self.players:
                x.available_actions = [Fold,Call,Raise]


    # def update_available_actions(self):
    #     if max(self.bets) == 0:
    #         for x in self.players:
    #             if x.stack < self.minimum_bet:
    #                 x.available_actions = [Fold,Check,Allin]
    #             else:
    #                 x.available_actions = [Fold,Check,Bet]

    #     elif self.stage == Preflop and max(self.bets) == self.blinds[1]:
    #         for x in self.players:
    #             if x.stack < max(self.bets):
    #                 x.available_actions = [Fold,Allin]
    #             elif x.stack < self.minimum_raise:
    #                 x.available_actions = [Fold,Call,Allin]
    #             else:
    #                 x.available_actions = [Fold,Call,Raise]

    #         if self.players[self.bb].stack < self.minimum_raise:
    #             self.players[self.bb].available_actions = [Fold,Check,Allin]
    #         else:
    #             self.players[self.bb].available_actions = [Fold,Check,Raise]

    #     else:
    #         for x in self.players:
    #             if x.stack < max(self.bets):
    #                 x.available_actions = [Fold,Allin]
    #             elif x.stack < self.minimum_raise:
    #                 x.available_actions = [Fold,Call,Allin]
    #             else:
    #                 x.available_actions = [Fold,Call,Raise]


    def is_stage_done(self):
        if [x.folded for x in self.players].count(False) == 1:
            for i in xrange(self.nplayers):
                if not self.players[i].folded:
                    self.winners.append(i)

            return AllFold

        if all([x.folded or x.at_least_one_action for x in self.players]):
            _lst = []
            for i in xrange(self.nplayers):
                if not self.players[i].folded:
                    _lst.append(self.bets[i])

            if max(_lst) == min(_lst):
                if self.stage == River:
                    return ShowDown
                else:
                    return StageEnd

        return False


    def stage_str(self):
        if self.stage == Deal:
            return 'Deal'
        elif self.stage == Preflop:
            return 'Preflop'
        elif self.stage == Flop:
            return 'Flop'
        elif self.stage == Turn:
            return 'Turn'
        elif self.stage == River:
            return 'River'


    def adjust(self,stagedone):
        if stagedone == AllFold:
            self.collect_pot()
            self.players[self.winners[0]].stack += self.pot
            self.action_history_update('%s won the pot (+ %d)'%(self.players[self.winners[0]].name,self.pot))

        elif stagedone == ShowDown:
            self.collect_pot()
            n = len(self.winners)
            if n == 1:
                self.players[self.winners[0]].stack += self.pot
                self.action_history_update(
                    '%s won the pot by showdown (+ %d)'%(self.players[self.winners[0]].name,self.pot))
                self.action_history_update(
                    '    hand : %s (%s)'%(pu.hand_to_str(self.players[self.winners[0]].best_hand[0]),
                                          pu.handrank_to_str(self.players[self.winners[0]].best_hand[1])))
            else:
                p = self.pot
                q = p / n
                r = p % n
                s = self.sb
                while p > 0:
                    if s in self.winners:
                        self.players[s].stack += q
                        p -= q
                        pp = q
                        if r > 0:
                            self.players[s].stack += 1
                            r -= 1
                            p -= 1
                            pp += 1

                        self.action_history_update(
                            '%s won the pot by showdown (+ %d)'%(self.players[s].name,pp))
                        self.action_history_update(
                            '    hand : %s (%s)'%(pu.hand_to_str(self.players[s].best_hand[0]),
                                                  pu.handrank_to_str(self.players[s].best_hand[1])))

                    s = (s+1)%self.nplayers



    ### player action

    def a_fold(self,player):
        self.players[player].folded = True
        self.update_available_actions()
        self.players[player].at_least_one_action = True
        self.action_history_update('%s folded'%self.players[player].name)


    def a_call(self,player):
        _max = max(self.bets)
        _cur = self.bets[player]
        _dif = _max - _cur
        self.bets[player] += _dif
        self.players[player].stack -= _dif
        self.update_current_pot()
        self.update_available_actions()
        self.players[player].at_least_one_action = True
        if _dif == 0:
            self.action_history_update('%s checked'%(self.players[player].name))
        else:
            self.action_history_update('%s called %d'%(self.players[player].name,_dif))


    def a_bet(self,player,value,ante=False):
        self.bets[player] += value
        self.players[player].stack -= value
        self.update_current_pot()
        self.update_available_actions()
        self.players[player].at_least_one_action = True
        self.minimum_raise = value+value
        if not ante:
            self.action_history_update('%s betted %d'%(self.players[player].name,value))


    def a_raiseto(self,player,value):
        _max = max(self.bets)
        _cur = self.bets[player]
        _dif = value - _cur
        self.bets[player] += _dif
        self.players[player].stack -= _dif
        self.update_current_pot()
        self.update_available_actions()
        self.players[player].at_least_one_action = True
        self.minimum_raise = 2*value-_max
        self.action_history_update('%s raised to %d'%(self.players[player].name,value))


    # def a_raiseby(self,player,value):
    #     _max = max(self.bets)
    #     _cur = self.bets[player]
    #     _dif = _max + value - _cur
    #     self.bets[player] += _dif
    #     self.players[player].stack -= _dif
    #     self.update_current_pot()
    #     self.update_available_actions()
    #     self.players[player].at_least_one_action = True
    #     self.minimum_raise = value+_dif
    #     self.action_history_update('%s raised by %d'%(self.players[player].name,value))


    # def a_allin(self,player):
    #     _stack = self.players[player].stack
    #     _max = max(self.bets)
    #     if stack >= self.minimum_raise:
    #         pass
    #     elif stack >= _max:
    #         pass
    #     elif stack >= self.minimum_bet:
    #         pass
    #     else:
    #         pass

    #     self.players[player].allin = True
    #     self.update_available_actions()
    #     self.players[player].at_least_one_action = True


    ### utilities

    def clear_bets(self):
        self.bets = self.zerobets[:]


    def collect_pot(self):
        self.pot += sum(self.bets)
        self.clear_bets()


    def update_current_pot(self):
        self.current_pot = self.pot + sum(self.bets)


    def next_player(self, candidate=-1):
        if candidate != -1:
            nextp = candidate
        else:
            nextp = (self.current_player+1)%self.nplayers

        # while self.players[nextp % self.nplayers].folded or self.players[nextp % self.nplayers].allin:
        while self.players[nextp % self.nplayers].folded:
            nextp += 1

        self.current_player = nextp % self.nplayers


    def reset_at_least_one_action(self):
        for x in self.players:
            x.at_least_one_action = False


    def action_history_update(self,history):
        if len(self.action_history) > 1024:
            self.action_history.pop(0)

        self.action_history.append('[%s]  '%(datetime.now().strftime('%H:%M:%S'))+history)


    def reset_minimum(self):
        self.minimum_bet = self.blinds[1]
        self.minimum_raise = 0





# if __name__ == '__main__':
#     sys.exit(1)
