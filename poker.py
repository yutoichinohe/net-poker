#!/usr/bin/env python

import sys, os, math, commands
import random, itertools, copy
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
Allin = 6

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
        self.allin = False
        self.available_actions = []
        self.at_least_one_action = False


class Game:

    ### game control

    def __init__(self,nplayers,init_stack=500,blinds=(1,2,0)):
        if nplayers > 23:
            raise RuntimeError, 'too many players'
        elif nplayers < 2:
            raise RuntimeError, 'find a friend'
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
        self.pot            = {}
        self.stage          = Deal
        self.current_player = 0
        self.flop           = []
        self.turn           = []
        self.river          = []
        self.board          = []
        self.winners        = {}
        self.best_hands     = []


    def prepare(self):
        self.reset()
        self.button = (self.button+1)%self.nplayers

        d = pu.Deck()
        for x in self.players:
            x.hand = d.draw_top(2)
            x.best_hand = []
            x.folded = False
            x.allin = False
            x.available_actions = []
            x.at_least_one_action = False

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
        self.reset_minimum()
        self.collect_pot()

        if self.stage == Deal:
            self.stage = Preflop
            self.next_player(candidate=(self.sb+2)%self.nplayers)
            self.a_bet(self.sb,self.blinds[0],ante=True)
            self.a_bet(self.bb,self.blinds[1],ante=True)
        elif self.stage == Preflop:
            self.stage = Flop
            self.next_player(candidate=(self.button+1)%self.nplayers)
            self.board = self.board + self.flop
        elif self.stage == Flop:
            self.stage = Turn
            self.next_player(candidate=(self.button+1)%self.nplayers)
            self.board = self.board + self.turn
        elif self.stage == Turn:
            self.stage = River
            self.next_player(candidate=(self.button+1)%self.nplayers)
            self.board = self.board + self.river

        self.update_available_actions()
        self.reset_at_least_one_action()


    def showdown(self):
        self.assign_best_hands()
        for k in self.pot.keys():
            l = []
            for i in k:
                if not self.players[i].folded:
                    l.append(i)

            bests = self.showdown_players(l)
            self.winners[tuple(l)] = bests


    def showdown_players(self,players_i_list):
        best_hands = [self.best_hands[i] for i in players_i_list]
        current_best = [players_i_list[0]]
        current_best_hand = [best_hands[0]]
        for ii in xrange(len(best_hands)-1):
            i = ii+1
            headsup = pu.heads_up(current_best_hand[0],best_hands[i])
            if headsup == 1:
                pass
            elif headsup == 0:
                current_best.append(players_i_list[i])
                current_best_hand.append(best_hands[i])
            else:
                current_best = [players_i_list[i]]
                current_best_hand = [best_hands[i]]

        return current_best


    def assign_best_hands(self):
        self.best_hands = []
        for x in self.players:
            if not x.folded:
                _bh = pu.best_hand(x.hand,self.board)
            else:
                _bh = ([],-1)

            self.best_hands.append(_bh)
            x.best_hand = _bh


    # def update_available_actions(self):
    #     if max(self.bets) == 0:
    #         for x in self.players:
    #             x.available_actions = [Fold,Check,Bet]

    #     elif self.stage == Preflop and max(self.bets) == self.blinds[1]:
    #         for x in self.players:
    #             x.available_actions = [Fold,Call,Raise]

    #         self.players[self.bb].available_actions = [Fold,Check,Raise]

    #     else:
    #         for x in self.players:
    #             x.available_actions = [Fold,Call,Raise]


    def update_available_actions(self):
        if max(self.bets) == 0:
            for x in self.players:
                if x.stack <= self.minimum_bet:
                    x.available_actions = [Fold,Check,Allin]
                else:
                    x.available_actions = [Fold,Check,Bet]

        elif self.stage == Preflop and max(self.bets) == self.blinds[1]:
            for i in xrange(self.nplayers):
                x = self.players[i]
                if x.stack+self.bets[i] <= max(self.bets):
                    x.available_actions = [Fold,Allin]
                elif x.stack+self.bets[i] <= self.minimum_raise:
                    x.available_actions = [Fold,Call,Allin]
                else:
                    x.available_actions = [Fold,Call,Raise]

            if self.players[self.bb].stack <= self.minimum_raise:
                self.players[self.bb].available_actions = [Fold,Check,Allin]
            else:
                self.players[self.bb].available_actions = [Fold,Check,Raise]

        else:
            for i in xrange(self.nplayers):
                x = self.players[i]
                if x.stack+self.bets[i] <= max(self.bets):
                    x.available_actions = [Fold,Allin]
                elif x.stack+self.bets[i] <= self.minimum_raise:
                    x.available_actions = [Fold,Call,Allin]
                else:
                    x.available_actions = [Fold,Call,Raise]


    def adjust(self,stagedone):
        if stagedone == AllFold:
            self.collect_pot()
            _val = sum(self.pot.values())
            _wnr = self.players[self.winners.values()[0]]
            _wnr.stack += _val
            self.action_history_update('%s won the pot (+ %d)'%(_wnr.name,_val))

        elif stagedone == ShowDown:
            self.collect_pot()
            for k,v in self.winners.items():
                n = len(v)
                if n == 1:
                    _val = self.pot[k]
                    _wnr = self.players[v[0]]
                    _wnr.stack += _val
                    self.action_history_update('%s won the pot by showdown (+ %d)'%(_wnr.name,_val))
                    self.action_history_update('    hand : %s (%s)'%(pu.hand_to_str(_wnr.best_hand[0]),
                                                                     pu.handrank_to_str(_wnr.best_hand[1])))
                else:
                    p = self.pot[k]
                    q = p / n
                    r = p % n
                    s = self.sb
                    while p > 0:
                        if s in v:
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
        self.update_available_actions()
        self.players[player].at_least_one_action = True
        if self.players[player].stack == 0:
            self.players[player].allin = True

        if _dif == 0:
            self.action_history_update('%s checked'%(self.players[player].name))
        else:
            self.action_history_update('%s called %d'%(self.players[player].name,_dif))


    def a_bet(self,player,value,ante=False):
        self.bets[player] += value
        self.players[player].stack -= value
        self.minimum_raise = value+value
        self.update_available_actions()
        self.players[player].at_least_one_action = True
        if self.players[player].stack == 0:
            self.players[player].allin = True

        if not ante:
            self.action_history_update('%s betted %d'%(self.players[player].name,value))


    def a_raiseto(self,player,value):
        _max = max(self.bets)
        _cur = self.bets[player]
        _dif = value - _cur
        self.bets[player] += _dif
        self.players[player].stack -= _dif
        self.minimum_raise = 2*value-_max
        self.update_available_actions()
        self.players[player].at_least_one_action = True
        if self.players[player].stack == 0:
            self.players[player].allin = True

        self.action_history_update('%s raised to %d'%(self.players[player].name,value))


    def a_allin(self,player):
        _to_call = max(self.bets)
        _cur = self.bets[player]
        _stack = self.players[player].stack
        self.bets[player] += _stack
        self.players[player].stack -= _stack

        _value = self.bets[player]

        if _to_call > 0:
            if _value >= _to_call: ## raise failed -- call+extra
                self.minimum_raise = self.minimum_raise+_value-_to_call
            else: ## call failed -- fold(allin)
                pass
        else: ## bet failed -- check+extra
            self.minimum_raise = self.minimum_bet+_value

        self.update_available_actions()
        self.players[player].at_least_one_action = True
        self.players[player].allin = True


    ### utilities

    def clear_bets(self):
        self.bets = self.zerobets[:]


    def collect_pot(self):
        _entitled = []
        for i in xrange(self.nplayers):
            if self.players[i].allin:
                _bet = self.bets[i]
                _sum = 0
                for b in self.bets:
                    if b <= _bet:
                        _sum += b
                    else:
                        _sum += _bet

                _entitled.append((i,_sum))

            elif self.players[i].folded:
                pass

            else:
                _entitled.append((i,sum(self.bets)))

        _entitled_sorted = sorted(_entitled, key=lambda x: x[1])
        _notfolded = sorted([x[0] for x in _entitled])

        for i in xrange(len(_entitled_sorted)):
            if all([x[1]<=0 for x in _entitled_sorted]):
                break

            _v = _entitled_sorted[i][1]
            if _v == 0:
                _notfolded.remove(_entitled_sorted[i][0])
                continue

            self.pot[tuple(_notfolded)] = self.pot.get(tuple(_notfolded),0) + _v
            _entitled_sorted = [(x[0],x[1]-_v) for x in _entitled_sorted]
            _notfolded.remove(_entitled_sorted[i][0])

        self.arrange_pot()
        self.clear_bets()


    def arrange_pot(self):
        p = {}
        for k,v in self.pot.items():
            l = []
            for i in k:
                if not self.players[i].folded:
                    l.append(i)

            p[tuple(l)] = p.get(tuple(l),0) + v

        self.pot = p


    def next_player(self, candidate=-1):
        if candidate != -1:
            nextp = candidate
        else:
            nextp = (self.current_player+1)%self.nplayers


        if not all([x.folded or x.allin for x in self.players]):
            while self.players[nextp % self.nplayers].folded or self.players[nextp % self.nplayers].allin:
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


    ### accessors, interfaces

    def is_stage_done(self):
        if [x.folded for x in self.players].count(False) == 1:
            winner = -1
            for i in xrange(self.nplayers):
                if not self.players[i].folded:
                    winner = i
                    break

            for k in self.pot.keys():
                self.winners[k] = winner

            return AllFold

        if (all([x.folded or x.at_least_one_action or x.allin for x in self.players]) or
            [x.folded or x.allin for x in self.players].count(False) == 1):
            _lst = []
            _maxallin = 0
            for i in xrange(self.nplayers):
                if self.players[i].allin and self.bets[i] > _maxallin:
                    _maxallin = self.bets[i]

                if not (self.players[i].folded or self.players[i].allin):
                    _lst.append(self.bets[i])

            if not _lst or max(_lst) == min(_lst) and min(_lst) >= _maxallin:
                if self.stage == River:
                    return ShowDown
                else:
                    return StageEnd

        return False


    def set_blinds(self,blinds):
        self.blinds = blinds
        self.minimum_bet = blinds[1]


    def set_stack(self,player,stack):
        self.players[player].stack = stack


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





# if __name__ == '__main__':
#     sys.exit(1)
