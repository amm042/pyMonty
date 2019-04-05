"""
Montey hall client
Alan Marchiori 2019
"""
import logging
import socket
import time
import argparse

def main(addr, port, delay):
    log = logging.getLogger()
    server_port = (addr, port)

    log.info("Starting game with {}".format(server_port))

    #for k in range(10):
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as skt:

            # socket options defined here https://linux.die.net/man/3/setsockopt
            if skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1):
                log.error("setsockopt failed.")
                exit(-1)
            skt.connect(server_port)

            log.info("Game started with {}".format(
                server_port
            ))
            skt.send(b"PLAYALAN")
            rsp = skt.recv(4096).decode('utf-8').strip()
            log.info("Got: {} {}".format(rsp, rsp=='WAIT'))

            if rsp == 'WAIT':
                log.info("ABORT")
                time.sleep(0.1)
                continue

            skt.send(b"OPEN0")
            rsp = skt.recv(4096).decode('utf-8')
            log.info("Got: {}".format(rsp))
            skt.send(b"DONE")
            rsp = skt.recv(4096).decode('utf-8')
            log.info("Got: {}".format(rsp))
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__)
    parser.add_argument(
        '-a', '--addr', type=str,
        help='ip address of the server', required=False,
        default="127.0.0.1")
    parser.add_argument(
        '-p', '--port', type=int,
        help='port the server listens on', required=False,
        default=8888)
    parser.add_argument(
        '-d', '--delay', type=int,
        help='delay in seconds', required=False,
        default=1)
    FORMAT = '%(asctime)-15s %(levelname)-6s: %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    args = parser.parse_args()

    # args must match main's parameters!
    main(**vars(args))
