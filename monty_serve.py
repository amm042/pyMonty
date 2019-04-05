"""
Montey hall server
Alan Marchiori 2019
"""
import logging
import socket
import time
import argparse
import datetime
import threading
import string
import pickle
from queue import Queue, Empty
import os.path

from monty import MhGame
from pprint import pprint



games = {}
result_q = Queue()
shutdown_e = threading.Event()
results = {}

def reject(skt, addr, log):
    log.info("Connection throttled [TOOSOON]: {}".format(
        addr
    ))
    skt.send("WAIT\n".encode())
    skt.close()

def main(addr, port, delay):
    log = logging.getLogger()
    server_port = (addr, port)


    log.info("Starting server on {}".format(server_port))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as skt:

        # socket options defined here https://linux.die.net/man/3/setsockopt
        if skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1):
            log.error("setsockopt failed.")
            exit(-1)
        skt.bind(server_port) # bind socket to the TCP port
        skt.settimeout(1) # to keep from blocking

        # now the server is bound, we have to first accept
        # conections and then we can communicate
        skt.listen() # listen for connections

        # this assumes we close the client socket before
        # the next client connects
        while shutdown_e.is_set() == False:
            # This blocks until a connection is made
            # it returns a new (connected) socket object and the
            # remote address
            try:
                clientsocket, clientaddress = skt.accept()
            except socket.timeout:
                #log.info("timeout on accept")
                continue

            now = datetime.datetime.now()

            if clientaddress[0] in games:
                cgame = games[clientaddress[0]]

                if (now - cgame['time']).total_seconds() < delay:
                    reject(clientsocket, clientaddress, log)
                    continue
                else:
                    del games[clientaddress[0]]

            g = MhGame(clientaddress, clientsocket, result_q)
            cgame = {
                'active':True,
                'socket': clientsocket,
                'time': now,
                'game': g,
                'thread': threading.Thread(
                    target = g.play,
                    name = str(g)
                )
            }
            games[clientaddress[0]] = cgame

            log.info("Game started {}".format(
                clientaddress
            ))
            cgame['thread'].start()

def cleanstr(s, n=20):
    "clean string to printable chars with max length n"

    if s == None:
        return "NONE"

    try:
        s = s.decode()
    except AttributeError:
        pass

    try:
        q = ''.join(x for x in s[:n] if x in string.printable[:64])

    except TypeError:
        q = "TypeError"

    return q

def run_ui():

    while True:

        try:

            while True:
                r = result_q.get(block=False)

                date, client, name, score = r

                if client in games:
                    del games[client]

                if score == None:
                    continue

                if name in results:
                    t = results[name]
                    t[0] += 1 # num games
                    t[1] += score # total score
                    t[2] += 1 if score>0 else 0 # correct games
                else:
                    results[name] = [1, score, 1 if score>0 else 0]

        except Empty:
            pass

        print(65*"\n")

        print(65*"=")
        print("{}  ----  {} games".format(
            datetime.datetime.now(),
            len(games)))

        for client, gameinfo in games.items():
            g = gameinfo['game']
            print("  {} :: {} :: {}".format(client,
                                            g.name,
                                            g.prize))
        print(65*"=")


        print("TOTAL SCORES")


        print("{:20} {:>10} {:>20} {:>12}".format(
            "NAME",
            "GAMES",
            "SCORE",
            "ACCURACY(%)"
        ))
        print(65*"-")

        fmts = "{:20} {:10d} {:20d}     {:>3.3f}%"
        strs = []
        for name, z in results.items():
            usergames, score, wins = z

            acc = wins/usergames

            try:
                strs.append(
                    (acc,
                        fmts.format(
                            cleanstr(name,20),
                            usergames,
                            score,
                            100*acc
                    )))
            except Exception as x:
                strs.append(str(x))
                continue

        for s in sorted(strs, key=lambda x: x[0], reverse=True):
            print(s[1])

        print(65*"=")
        time.sleep(0.2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__)
    parser.add_argument(
        '-a', '--addr', type=str,
        help='ip address of the server', required=False,
        default="")
    parser.add_argument(
        '-p', '--port', type=int,
        help='port the server listens on', required=False,
        default=8888)
    parser.add_argument(
        '-d', '--delay', type=int,
        help='minimum delay in seconds', required=False,
        default=1)

    debug = False

    if debug:
        FORMAT = '%(asctime)-15s %(levelname)-6s: %(message)s'
        logging.basicConfig(format=FORMAT, level=logging.DEBUG)

    args = parser.parse_args()


    # startup server thread
    # args must match main's parameters!
    server_thread = threading.Thread(
        name="Main TCP server",
        target = main,
        args = (args.addr, args.port, args.delay)
    )
    server_thread.start()

    savefile = "monty_state.pickle"
    if os.path.exists(savefile):
        with open(savefile, 'rb') as f:
            results = pickle.load(f)
    #log = logging.getLogger()
    try:
        if debug:
            while True:
                time.sleep(1)
        else:
            run_ui()
    except KeyboardInterrupt:
        print("Ctrl-c, quit")

    with open(savefile,'wb') as f:
        pickle.dump(results, f)

    shutdown_e.set()
    server_thread.join()

    print("Shutdown complete.")
