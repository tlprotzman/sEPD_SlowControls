"""
Tristan Protzman
Jul 20 2023
"""

import socket
import sys
import struct
import pickle
import time
import logging

HOST, PORT = "localhost", 12345

def receive(conn):
    # data_size = conn.recv(4).decode()
    
    data_size = struct.unpack('>I', conn.recv(4))[0]
    logging.info("Receiving {} bytes".format(data_size))
    received_payload = b""
    reamining_payload_size = data_size
    while reamining_payload_size != 0:
        received_payload += conn.recv(reamining_payload_size)
        reamining_payload_size = data_size - len(received_payload)
    data = pickle.loads(received_payload)
    logging.info("Received {}".format(data))
    return data


logging.basicConfig(level=logging.WARNING)

if len(sys.argv) == 1:
    sys.exit(1)

if sys.argv[1] == "t":
    card = 0
    try:
        card = int(sys.argv[2])
    except:
        print("Specify interface board number - no request sent")
        sys.exit(1)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        sock.sendall(bytes("temperature {}\n".format(card), "utf-8"))
        print(receive(sock))

if sys.argv[1] == "v":
    card = 0
    try:
        card = int(sys.argv[2])
    except:
        print("Specify interface board number - no request sent")
        sys.exit(1)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        sock.sendall(bytes("voltage {}\n".format(card), "utf-8"))
        print(receive(sock))

if sys.argv[1] == "i":
    card = 0
    try:
        card = int(sys.argv[2])
    except:
        print("Specify interface board number - no request sent")
        sys.exit(1)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        sock.sendall(bytes("current {}\n".format(card), "utf-8"))
        print(receive(sock))

if sys.argv[1] == "s":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        sock.sendall(bytes("shutdown\n", "utf-8"))

if sys.argv[1] == "h":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        sock.sendall(bytes("help\n", "utf-8"))
        print(receive(sock))
