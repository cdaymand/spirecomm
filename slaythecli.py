#!/usr/bin/env python3

from argparse import ArgumentParser

from spirecomm.slaythecli import client, server


def main():
    parser = ArgumentParser()
    parser.add_argument('mode', choices=['client', 'server'], help="client or server")
    parser.add_argument('--ip', type=str, default="127.0.0.1", nargs="?", help="The server IP to bind to")
    parser.add_argument('--port', type=int, default=8080, nargs="?", help="The server port")
    parser.add_argument("--accessibility", help="To make it accessible", action="store_true")
    parser.add_argument("-v", "--verbose", help="Add some logging", action="store_true")
    args = parser.parse_args()
    if args.mode == 'server':
        server.main(ip=args.ip, port=args.port)
    elif args.mode == 'client':
        client.main(ip=args.ip, port=args.port, accessibility=args.accessibility, verbose=args.verbose)


if __name__ == "__main__":
    main()
