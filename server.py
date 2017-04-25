#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, math, commands
import time, socket, threading

import poker
import poker_util as pu

# argvs = sys.argv
# if len(argvs)-1 < 1:
#     print 'usage : %s [#players]'%os.path.basename(argvs[0])
#     quit()

nplayers = 3
host     = 'localhost'
port     = 37564

action_history_length = 20

class WorkerThread(threading.Thread):

    def __init__(self,s_socket,threadindex):
        threading.Thread.__init__(self,args=(),kwargs=None)
        self.ssock = s_socket
        self.threadindex = threadindex
        self.ready = False
        self.name = ''
        self.op = ''
        self.buffer = ''
        self.action = ''
        self.action_value = -1
        self.minimum_bet = 0
        self.minimum_raise = 0


    def run(self):
        while True:
            time.sleep(0.001)
            self.csock, (self.caddr, self.cport) = self.ssock.accept()
            print('New client: {0}:{1}'.format(self.caddr, self.cport))

            while True:
                time.sleep(0.001)
                if self.op == 'askname':
                    self.send_message('Name? : ')
                    self.name = self.recv_message().strip()
                    print('Thread {0} ({1}:{2}) name : {3}'.format(self.threadindex,self.caddr,
                                                                   self.cport,self.name))
                    self.ready = True
                    self.op = ''

                elif self.op == 'action':

                    while len(self.action) != 1:
                        self.send_message('Action? (%s) : '%self.buffer[0])
                        self.action = self.recv_message().strip().lower()
                        if self.action in self.buffer[1]:
                            if self.action == 'f' or self.action == 'c':
                                pass
                            elif self.action == 'b':
                                _str = 'Value? (%d): '%self.minimum_bet
                                while self.action_value < self.minimum_bet:
                                    self.send_message(_str)
                                    try:
                                        self.action_value = int(self.recv_message().strip())
                                    except ValueError:
                                        self.action_value = -1

                                    if self.action_value == 0:
                                        self.action = ''
                                        self.action_value = -1
                                        break

                            elif self.action == 'r':
                                _str = 'Value? (%d): '%self.minimum_raise
                                while self.action_value < self.minimum_raise:
                                    self.send_message(_str)
                                    try:
                                        self.action_value = int(self.recv_message().strip())
                                    except ValueError:
                                        self.action_value = -1

                                    if self.action_value == 0:
                                        self.action = ''
                                        self.action_value = -1
                                        break

                            else:
                                self.action = ''
                        else:
                            self.action = ''


                    self.ready = True
                    self.buffer = ''
                    self.op = ''
                    self.minimum_bet = 0
                    self.minimum_raise = 0

                elif self.op == 'press_return':
                    self.send_message('Continue? [RET]')
                    self.recv_message().strip()
                    self.ready = True
                    self.op = ''



            self.csock.close()
            print('Bye-Bye: {0}:{1}'.format(self.caddr, self.cport))


    def ask_name(self):
        self.set_op('askname')


    def send_action_prompt(self,options,b,r):
        self.minimum_bet = b
        self.minimum_raise = r
        self.buffer = options
        self.set_op('action')


    def get_action(self):
        return self.action,self.action_value


    def press_return(self):
        self.set_op('press_return')


    def set_op(self,op):
        self.op = op
        self.ready = False


    def cleanup_action(self):
        self.ready = False
        self.buffer = ''
        self.action = ''
        self.action_value = -1


    def send_message(self,message):
        self.csock.sendall(message)


    def recv_message(self):
        while True:
            try:
                message = self.csock.recv(1024).strip()
                return message
            except OSError:
                break



class PokerServer:
    def __init__(self,nplayers,host,port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.sock.bind((host,port))
        self.sock.listen(128)

        self.threads = []
        self.nplayers = nplayers
        self.nthreads = nplayers

        for i in range(self.nthreads):
            thr = WorkerThread(self.sock, i)
            thr.daemon = True
            thr.start()
            self.threads.append(thr)


    def init_game(self,init_stack=500,blinds=(1,2,0)):
        self.g = poker.Game(self.nplayers, init_stack=init_stack, blinds=blinds)

        [x.ask_name() for x in self.threads]
        while not all([x.ready for x in self.threads]):
            pass

        [x.send_message('Everyone ready.\n') for x in self.threads]
        for i in xrange(self.nthreads):
            self.g.players[i].name = self.threads[i].name



    def single_game(self):
        self.g.prepare()
        self.sendall_situation()

        while True:
            while not self.g.is_stage_done():
                time.sleep(1.0)
                cp = self.g.current_player
                self.threads[cp].send_action_prompt(
                    self.action_options(self.g.players[cp].available_actions),
                    self.g.minimum_bet,self.g.minimum_raise)
                while not self.threads[cp].ready:
                    pass

                _a,_v = self.threads[cp].get_action()

                if _a == 'f':
                    self.g.a_fold(cp)
                elif _a == 'c':
                    self.g.a_call(cp)
                elif _a == 'b':
                    self.g.a_bet(cp,_v)
                elif _a == 'r':
                    self.g.a_raiseto(cp,_v)

                self.threads[cp].cleanup_action()
                self.g.next_player()
                self.sendall_situation()

            if self.g.is_stage_done() == poker.AllFold:
                break
            elif self.g.is_stage_done() == poker.StageEnd:
                self.g.proceed()
                self.sendall_situation()
            elif self.g.is_stage_done() == poker.ShowDown:
                self.g.showdown()
                break

        self.g.adjust(self.g.is_stage_done())
        self.sendall_situation(self.g.is_stage_done())

        [x.press_return() for x in self.threads]
        while not all([x.ready for x in self.threads]):
            pass


    def sendall_situation(self,situ=''):
        for i in xrange(self.nthreads):
            self.threads[i].send_message('\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n')
            self.threads[i].send_message(self.action_display())
            if situ == poker.ShowDown:
                self.threads[i].send_message(self.game_display(showdown=True))
            else:
                self.threads[i].send_message(self.game_display())

            self.threads[i].send_message(self.player_display(i))


    def action_options(self,available_actions):
        _str = ''
        _lst = []
        if poker.Fold in available_actions:
            _str += '[F]old '
            _lst.append('f')

        if poker.Check in available_actions:
            _str += '[C]heck '
            _lst.append('c')

        if poker.Call in available_actions:
            _str += '[C]all '
            _lst.append('c')

        if poker.Bet in available_actions:
            _str += '[B]et '
            _lst.append('b')

        if poker.Raise in available_actions:
            _str += '[R]aise '
            _lst.append('r')

        return _str.strip(), _lst


    def game_display(self,showdown=False):
        disp = '\n'
        _str = ' %s '%(self.g.stage_str())
        disp += '-------{s:{c}^{n}}-------'.format(s=_str,n=10,c='-')
        _str = ' ('+'-'.join([str(x) for x in self.g.blinds])+') '
        disp += '{s:{c}^{n}}\n\n'.format(s=_str,n=24,c='-')
        for i in xrange(self.nplayers):
            if i == self.g.current_player:
                _str = '*  '
            elif self.g.players[i].folded:
                _str = 'x  '
            else:
                _str = '   '

            disp += _str
            if i == self.g.button:
                __str = '(BTN)'
            elif i == self.g.sb:
                __str = '(sb)'
            elif i == (self.g.sb+1)%self.g.nplayers:
                __str = '(bb)'
            else:
                __str = ''

            _str = '%s%s'%(self.g.players[i].name,__str)
            disp += '%-21s:'%(_str)
            if showdown:
                if not self.g.players[i].folded:
                    disp += '  {s:{c}^{n}}/{ss:{c}^{nn}} {t} : {u} ({v})\n'.format(
                        s=self.g.bets[i],ss=self.g.players[i].stack,
                        c=' ',n=9,nn=10,
                        t=pu.hand_to_str(self.g.players[i].hand),
                        u=pu.hand_to_str(self.g.players[i].best_hand[0]),
                        v=pu.handrank_to_str(self.g.players[i].best_hand[1]))
                else:
                    disp += '  {s:{c}^{n}}/{ss:{c}^{nn}} Folded\n'.format(
                        s=self.g.bets[i],ss=self.g.players[i].stack,
                        c=' ',n=9,nn=10)
            else:
                disp += '  {s:{c}^{n}}/{ss:{c}^{nn}}\n'.format(
                    s=self.g.bets[i],ss=self.g.players[i].stack,c=' ',n=9,nn=10)

        disp += '\n'
        disp += '        Total pot       :   %-11s\n\n'%(self.g.current_pot)
        disp += '{s:{c}^{n}}\n\n'.format(s=pu.hand_to_str(self.g.board),c=' ',n=48)
        return disp


    def player_display(self,player):
        disp  = '---------------------- You ---------------------\n\n'
        if self.g.players[player].folded:
            _str = 'Folded (%s)'%(pu.hand_to_str(self.g.players[player].hand))
        else:
            _str = '%s'%(pu.hand_to_str(self.g.players[player].hand))

        disp += '{s:{c}^{n}}\n\n'.format(s=_str,c=' ',n=48)
        disp += 'Bet           {s:{c}^{n}} /   {ss:{c}^{nn}}     Stack\n\n'.format(
            s=self.g.bets[player],
            ss=self.g.players[player].stack,
            c=' ',n=9,nn=10)
        return disp


    def action_display(self):
        disp = '-------------------- Action --------------------\n\n'
        for i in xrange(action_history_length):
            ii = -action_history_length+i
            try:
                disp += '%s\n'%self.g.action_history[ii]
            except:
                pass

        return disp













def main():
    server = PokerServer(nplayers,host,port)

    server.init_game(100,(1,2,0))
    while True:
        server.single_game()
        # time.sleep(5.0)











if __name__ == '__main__':
    main()
