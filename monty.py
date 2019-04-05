import random
import logging
import socket
import queue
import datetime

class MhGame:
    def __init__(self, remote=None, skt=None, q=None):
        self.log = logging.getLogger(__name__)
        self.q = q
        self.remote = remote
        self.skt = skt
        if self.skt:
            self.skt.settimeout(30)
        self.doors = [100,0,0]
        self.opened= [0,0,0]
        self.doornames = [str(x) for x in range(len(self.doors))]
        self.select = None # first pick of user
        self.prize = None # once a door is opened this is your prize
        self.name = None # user name from play command
        random.shuffle(self.doors)

    def __str__(self):
        return 'MhGame {} ({})'.format(self.remote, self.name)

    def get_hint(self):
        "once a door is selected this will return another door that has zero value"
        hints = []
        for i in range(len(self.doors)):
            if i != self.select and self.doors[i] == 0:
                hints.append(i)

        if len(hints) > 0:
            return random.choice(hints)

        self.log.error("No door to hint!")
        return -1
    def penalty(self):
        if self.prize == None or self.prize >= 0:
            self.prize = -max(self.doors)
        else:
            #negative prize
            self.prize *= 2

        return self.prize

    def open(self, i):
        "open a door to reveal the prize!"

        if self.prize == None:
            self.prize = self.doors[i]
        else:
            self.log.info("Cheat detected, multiple open!")
            return self.penalty()
        return self.prize

    def read(self):
        try:
            d = self.skt.recv(4096).decode('utf-8').strip().strip(' ').upper()
        except socket.timeout:
            d = None
        return d
    def write(self, msg):
        return self.skt.send((msg+'\n').encode('utf-8'))
    def play(self):
        self.log.info("Begin session {}".format(self))

        try:
            gotplay= False
            while True:
                msg = self.read()

                if msg == "DONE":
                    self.write("GOODBYE")
                    break

                if msg[:4] == 'PLAY' and len(msg)>=8:
                    self.write("HIHI"+msg[4:])
                    self.name = msg[4:]
                    gotplay = True
                    continue

                #           012345
                # wait for "GUESSx"
                if msg[:4] == 'GUES' and msg[4] in self.doornames and gotplay:
                    self.select = int(msg[4])
                    # send back HINT
                    self.write("HINT"+str(self.get_hint()))
                    continue

                #           01234
                # wait for "OPENx"
                if msg[:4] == 'OPEN' and msg[4] in self.doornames and gotplay:
                    willopen = int(msg[4])
                    self.write("PRIZ"+str(self.open(willopen)))
                    continue

                self.write("WTF?")

                self.log.info("Bad format, got '{}'.".format(
                    self, open))
        except BrokenPipeError:
            self.log.info("Remote ({}) hungup, how rude.".format(self))
            self.penalty()
            self.skt = None
        finally:
            if self.skt:
                self.skt.close()

        if self.q:
            self.q.put((datetime.datetime.now(),
                        self.remote,
                        self.name,
                        self.prize))
        self.log.info("End session {}".format(self))

if __name__=="__main__":
    "test cases"
    FORMAT = '%(asctime)-15s %(levelname)-6s: %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    log =logging.getLogger()

    total = 0
    strategies = ['neverchange', # gives 1/3 odds
                  'randomchange',# gives 1/2 odds
                  'alwayschange' # gives 2/3 odds
                  ]
    strategy = strategies[2]
    for i in range (1000):
        g = MhGame()
        guess = random.randint(0,2)
        g.select = guess
        hint = g.get_hint()

        check = [0, 1, 2]
        check.remove(guess)
        assert hint in check, "Hint not in range!"
        check.remove(hint)
        assert len(check)==1, "should have only one option left!"

        if strategy == 'neverchange':
            open = guess
        elif strategy == 'randomchange':
            choices = [guess, check[0]]
            open = random.choice(choices)
        elif strategy == 'alwayschange':
            open = check[0]
        else:
            raise Exception("Bad strategy.")

        prize = g.open(open)

        log.info("{}: guess {}, selected {}, got {}".format(
            i,
            guess,
            open,
            prize))
        total += prize
    i+=1
    print("Total prizes {} in {} games = {}".format(
        total, i, total/i
    ))
