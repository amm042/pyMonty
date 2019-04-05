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
from http.server import HTTPServer, BaseHTTPRequestHandler
from queue import Queue, Empty
import os.path
from monty import MhGame
from pprint import pprint

games = {}
result_q = Queue()
shutdown_e = threading.Event()
results = {}
web_q = Queue()

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

class web_ui(BaseHTTPRequestHandler):

    html = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Montey Hall Server</title>
    <link rel="icon" href="favicon.ico" />
    <link rel="stylesheet" href="https://unpkg.com/purecss@1.0.0/build/pure-min.css" integrity="sha384-nn4HPE8lTHyVtfCBi5yW9d20FjT8BJwUXyWZT9InLYax14RDjBj46LmSztkmNP9w" crossorigin="anonymous">
  </head>
  <body>
    <div id="results"></div>
    <script type="text/javascript">
        addEventListener('DOMContentLoaded', (event) => {
            console.log('Loading timer');
            setInterval(() =>{
                fetch('/data')
                    .then(resp => resp.text())
                    .then(text => {
                        document.getElementById("results").innerHTML =
                            "<pre>"+text+"</pre>";
                    })
                    .catch(err =>{
                        console.log("Fetch error: " + err);
                    })
            }, 333)
        });
    </script>
  </body>
</html>"""

    def do_GET(self):
        log = logging.getLogger("HttpHandler")

        if self.path == '/data':
            #log.info("DATA REQ")
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()

            self.wfile.write(web_q.get().encode())
        elif self.path == '/':
            #log.info("DEFAULT REQ")
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(web_ui.html.encode())
        elif self.path.startswith('/favicon.ico'):
            self.send_response(200)
            self.send_header("Content-type", "image/x-icon")
            self.end_headers()
            with open('favicon.ico', 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, 'That is not possible.')
def run_ui(debug=False):
    "when debug is set it does not display on screen so you can see log messages."
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

        now = str(datetime.datetime.now())

        if not debug:
            print(65*"\n") #simple clear screen :)
            print(65*"=")
            print("{}  ----  {} games".format(
                now,
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

        sorted_scores = sorted(strs, key=lambda x: x[0], reverse=True)


        if web_q.empty():
            # if the web server needs data, feed it.
            scoretext = [x[1] for x in sorted_scores]
            web_q.put(now + "\r\n" + "\r\n".join(scoretext))

        if not debug:
            for s in sorted_scores:
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
        '-u', '--ui-port', type=int,
        help='port the web-ui listens on', required=False,
        default=4181)
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

    print("Started http server on {}".format(
        (args.addr, args.ui_port)))
    # create web server thread
    httpd = HTTPServer(
                (args.addr, args.ui_port),
                web_ui)
    http_thread = threading.Thread(
        name="HTTP server",
        target = httpd.serve_forever
    )
    http_thread.daemon = True
    http_thread.start()

    try:
        run_ui(debug)
    except KeyboardInterrupt:
        print("Ctrl-c, quit")

    with open(savefile,'wb') as f:
        pickle.dump(results, f)

    shutdown_e.set()
    httpd.server_close()
    server_thread.join()

    print("Shutdown complete.")
