#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os
import time, socket, threading

import poker
import poker_util as pu
import blindgen as bg
import setup

#### setup

stage_duration_sec = setup.StageDurationSec
blindgen = setup.BlindGen
action_history_length = setup.ActionHistoryLength

#### Class, Function

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
            time.sleep(0.01)
            self.csock, (self.caddr, self.cport) = self.ssock.accept()
            print('New client: {0}:{1}'.format(self.caddr, self.cport))

            while True:
                time.sleep(0.01)
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
                            if self.action == 'f' or self.action == 'c' or self.action == 'a':
                                pass
                            elif self.action == 'b':
                                self.loop_until_valid_value(self.minimum_bet)
                            elif self.action == 'r':
                                self.loop_until_valid_value(self.minimum_raise)
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


    def send_action_prompt(self,options,b,r,s):
        self.minimum_bet = b
        self.minimum_raise = r
        self.stack = s
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
        try:
            self.csock.sendall(message)
        except:
            pass


    def recv_message(self):
        while True:
            try:
                message = self.csock.recv(1024).strip()
                return message
            except OSError:
                break


    def loop_until_valid_value(self,minvalue):
        _str = 'Value? (%d-%d): '%(minvalue,self.stack)
        while self.action_value < minvalue or self.action_value > self.stack:
            self.send_message(_str)
            try:
                self.action_value = int(self.recv_message().strip())
            except ValueError:
                self.action_value = -1

            if self.action_value == 0:
                self.action = ''
                self.action_value = -1
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

        print('Server ready')


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
                    self.g.minimum_bet,self.g.minimum_raise,self.g.players[cp].stack+self.g.bets[cp])
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
                elif _a == 'a':
                    self.g.a_allin(cp)

                self.threads[cp].cleanup_action()
                self.g.next_player()
                self.sendall_situation()

            isd = self.g.is_stage_done()
            if isd == poker.AllFold:
                break
            elif isd == poker.StageEnd:
                self.g.proceed()
                self.sendall_situation()
            elif isd == poker.ShowDown:
                self.g.showdown()
                break

        isd = self.g.is_stage_done()
        self.g.adjust(isd)
        self.sendall_situation(isd)

        _alive = []
        for i in xrange(self.nplayers):
            if not self.g.players[i].eliminated:
                self.threads[i].press_return()
                _alive.append(i)

        if len(_alive) == 1:
            self.g.action_history_update('GAME END : %s won the game'%self.g.players[_alive[0]].name)
            self.sendall_situation()
            quit()

        while not all([x.ready for x in [self.threads[i] for i in _alive]]):
            pass


    def sendall_situation(self,situ=''):
        for i in xrange(self.nthreads):
            self.threads[i].send_message('\n\n\n\n\n\n\n\n\n\n')
            self.threads[i].send_message('\n\n\n\n\n\n\n\n\n\n')
            self.threads[i].send_message('\n\n\n\n\n\n\n\n\n\n')
            self.threads[i].send_message('\n\n\n\n\n\n\n\n\n\n')
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

        if poker.Allin in available_actions:
            _str += '[A]llin '
            _lst.append('a')

        return _str.strip(), _lst


    def game_display(self,showdown=False):
        disp = '\n'
        _str = ' %s '%(self.g.stage_str())
        disp += '-------{s:{c}^{n}}-------'.format(s=_str,n=10,c='-')
        _str = ' ('+'-'.join([str(x) for x in self.g.blinds])+') '
        disp += '{s:{c}^{n}}\n\n'.format(s=_str,n=24,c='-')
        for i in xrange(self.nthreads):
            if self.g.players[i].eliminated:
                _str = '-  '
            elif i == self.g.current_player:
                _str = '*  '
            elif self.g.players[i].folded:
                _str = 'x  '
            elif self.g.players[i].allin:
                _str = 'A  '
            else:
                _str = '   '

            disp += _str
            if i == self.g.button:
                if i == self.g.sb:
                    __str = '(BTN,sb)'
                else:
                    __str = '(BTN)'
            elif i == self.g.sb:
                __str = '(sb)'
            elif i == self.g.bb:
                __str = '(bb)'
            else:
                __str = ''

            _str = '%s%s'%(self.g.players[i].name,__str)
            disp += '%-21s:'%(_str)
            if showdown:
                if self.g.players[i].eliminated:
                    _t = pu.hand_to_str(self.g.players[i].hand)
                    _u = pu.hand_to_str(self.g.players[i].best_hand[0])
                    _v = pu.handrank_to_str(self.g.players[i].best_hand[1])
                    if _t and _u and _v:
                        disp += '  {s:{c}^{n}}/{ss:{c}^{nn}} {t} : {u} ({v})\n'.format(
                            s=self.g.bets[i],ss=self.g.players[i].stack,
                            c=' ',n=9,nn=10,t=_t,u=_u,v=_v)
                    else:
                        disp += '     ---   /   ---     Eliminated\n'

                elif not self.g.players[i].folded:
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
            elif self.g.players[i].eliminated:
                disp += '    ---    /   ---\n'
            else:
                disp += '  {s:{c}^{n}}/{ss:{c}^{nn}}\n'.format(
                    s=self.g.bets[i],ss=self.g.players[i].stack,c=' ',n=9,nn=10)

        disp += '\n'
        if not showdown:
            disp += '        side pot               enitled          \n\n'
            for k,v in self.g.pot.items():
                disp += '       %11s      : %s\n'%(v,','.join([self.g.players[i].name for i in k]))

        disp += '\n{s:{c}^{n}}\n\n'.format(s=pu.hand_to_str(self.g.board),c=' ',n=48)
        return disp


    def player_display(self,player):
        disp  = '---------------------- You ---------------------\n\n'
        if self.g.players[player].eliminated:
            _hand = pu.hand_to_str(self.g.players[player].hand)
            if _hand:
                _str = 'Eliminated (%s)'%(_hand)
            else:
                _str = 'Eliminated'
        elif self.g.players[player].folded:
            _str = 'Folded (%s)'%(pu.hand_to_str(self.g.players[player].hand))
        elif self.g.players[player].allin:
            _str = 'All-in (%s)'%(pu.hand_to_str(self.g.players[player].hand))
        else:
            _str = '%s'%(pu.hand_to_str(self.g.players[player].hand))

        disp += '{s:{c}^{n}}\n\n'.format(s=_str,c=' ',n=48)
        disp += 'Bet           {s:{c}^{n}} /   {ss:{c}^{nn}}     Stack\n\n'.format(
            s=self.g.bets[player],ss=self.g.players[player].stack,c=' ',n=9,nn=10)
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



#### Main body

def main():

    argvs = sys.argv
    if len(argvs)-1 != 3:
        print 'usage : %s [nplayers] [host (e.g. localhost)] [port (e.g. 37564)]'%os.path.basename(argvs[0])
        print '        use NETCAT to connect to the server: nc localhost 37564'
        quit()

    nplayers = int(argvs[1])
    host     = argvs[2]
    port     = int(argvs[3])


    bgen = bg.gen_blind_gen(blindgen)
    init_stack = bgen.init_stack
    init_blinds = bgen.structure[0]

    server = PokerServer(nplayers,host,port)
    server.init_game(init_stack,init_blinds)

    bgen.init(stage_duration_sec)

    while True:
        server.g.set_blinds(bgen.get_blinds())
        server.single_game()


if __name__ == '__main__':
    main()
