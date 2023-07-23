"""
Tristan Protzman
Jul 23 2023
"""

import socket
import sys
import struct
import pickle
import logging
import time

HOST, PORT = "localhost", 12345
interface_boards = 1

class sepdMonitor:
    # def __init__(self):
    #     pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.connect((HOST, PORT))

    def close(self):
        self.connection.close()

    def send(self, package):
        package = package + "\n"
        logging.info("Sending to server: {}".format(package))
        logging.debug("{} bytes".format(len(bytes(package, "utf-8"))))
        self.connection.sendall(bytes(package, "utf-8"))

    def receive(self):
        first_package = self.connection.recv(4)
        logging.debug("First package received: {}".format(first_package))
        data_size = struct.unpack('>I', first_package)[0]
        logging.debug("Receiving {} bytes".format(data_size))
        received_payload = b""
        reamining_payload_size = data_size
        while reamining_payload_size != 0:
            received_payload += self.connection.recv(reamining_payload_size)
            reamining_payload_size = data_size - len(received_payload)
        data = pickle.loads(received_payload)
        logging.info("Received from server: {}".format(data))
        return data

    def get_temperatures(self):
        logging.info("Getting temperature")
        temperatures = {}
        for i in range(interface_boards):
            package = "temperature {}".format(i)
            self.send(package)
            temperatures[i] = self.receive()
        logging.debug("Temperatures:")
        logging.debug(temperatures)
        return temperatures
    

    def get_voltages(self):
        logging.info("Getting voltage")
        voltages = {}
        for i in range(interface_boards):
            package = "voltage {}".format(i)
            self.send(package)
            voltages[i] = self.receive()
        logging.debug("voltages:")
        logging.debug(voltages)
        return voltages
    
    def get_currents(self):
        logging.info("Getting current")
        currents = {}
        for i in range(interface_boards):
            package = "current {}".format(i)
            self.send(package)
            currents[i] = self.receive()
        logging.debug("currents:")
        logging.debug(currents)
        return currents
    

    


logging.basicConfig(level=logging.DEBUG)
logging.debug("opening monitor")
with sepdMonitor() as monitor:
    for i in range(5):
        temperatures = monitor.get_temperatures()
        voltages = monitor.get_voltages()
        currents = monitor.get_currents()
        time.sleep(5)

