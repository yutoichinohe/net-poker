from datetime import datetime

def gen_blind_gen(str):
    if str == 'PokerStarsSNG':
        return PokerStarsSNG()
    elif str == 'FullTiltPokerSNG':
        return FullTiltPokerSNG()
    elif str == 'AJPC2014':
        return AJPC2014()
    elif str == 'WSOP2016':
        return WSOP2016()
    else:
        return BlindGenDefault()



class BlindGenDefault:
    def __init__(self):
        self.inittime = datetime.now()
        self.init_stack = 200
        self.structure = [(1,2,0)]

    def init(self,duration):
        self.duration = duration
        self.inittime = datetime.now()

    def get_blinds(self):
        now = datetime.now()
        tdiff = (now-self.inittime).seconds

        val = tdiff / self.duration
        if val >= len(self.structure)-1:
            return self.structure[-1]
        else:
            return self.structure[val]



class PokerStarsSNG(BlindGenDefault):
    def __init__(self):
        self.init_stack = 1500
        self.structure = [
            (  10,  20,  0),
            (  15,  30,  0),
            (  25,  50,  0),
            (  50, 100,  0),
            (  75, 150,  0),
            ( 100, 200,  0),
            ( 100, 200, 25),
            ( 200, 400, 25),
            ( 300, 600, 50),
            ( 400, 800, 50),
            ( 600,1200, 75),
            ( 800,1600, 75),
            (1000,2000,100),
            (1500,3000,150)]



class FullTiltPokerSNG(BlindGenDefault):
    def __init__(self):
        self.init_stack = 1500
        self.structure = [
            (  15,  30,0),
            (  20,  40,0),
            (  25,  50,0),
            (  30,  60,0),
            (  40,  80,0),
            (  50, 100,0),
            (  60, 120,0),
            (  80, 160,0),
            ( 100, 200,0),
            ( 120, 240,0),
            ( 150, 300,0),
            ( 200, 400,0),
            ( 250, 500,0),
            ( 300, 600,0),
            ( 400, 800,0),
            ( 500,1000,0),
            ( 600,1200,0),
            ( 800,1600,0),
            (1000,2000,0),
            (1200,2400,0),
            (1500,3000,0)]



class AJPC2014(BlindGenDefault):
    def __init__(self):
        self.init_stack = 3000
        self.structure = [
            (  25,  50,   0),
            (  50, 100,   0),
            (  75, 150,   0),
            ( 100, 200,   0),
            ( 150, 300,   0),
            ( 250, 500,   0),
            ( 400, 800,   0),
            ( 600,1200, 100),
            ( 800,1600, 200),
            (1000,2000, 300),
            (1500,3000, 500),
            (2000,4000, 500),
            (3000,6000,1000)]



class WSOP2016(BlindGenDefault):
    def __init__(self):
        self.init_stack = 50000
        self.structure = [
            (    75,   150,    0),
            (   150,   300,    0),
            (   150,   300,   25),
            (   200,   400,   50),
            (   250,   500,   75),
            (   300,   600,  100),
            (   400,   800,  100),
            (   500,  1000,  100),
            (   600,  1200,  200),
            (   800,  1600,  200),
            (  1000,  2000,  300),
            (  1200,  2400,  400),
            (  1500,  3000,  500),
            (  2000,  4000,  500),
            (  2500,  5000,  500),
            (  3000,  6000, 1000),
            (  4000,  8000, 1000),
            (  5000, 10000, 1000),
            (  6000, 12000, 2000),
            (  8000, 16000, 2000),
            ( 10000, 20000, 3000),
            ( 12000, 24000, 4000),
            ( 15000, 30000, 5000),
            ( 20000, 40000, 5000),
            ( 25000, 50000, 5000),
            ( 30000, 60000,10000),
            ( 40000, 80000,10000),
            ( 50000,100000,15000),
            ( 60000,120000,20000),
            ( 80000,160000,20000),
            (100000,200000,30000),
            (120000,240000,40000)]
