"""
Tristan Protzman
Jul 23 2023
"""

import json
import logging
import pickle
import socket
import struct
import sys
import time


class sepdMonitor:
    def __init__(self, config_file):
        if config_file is None:
            self.configs = self.load_configs()
        else:
            self.configs = self.load_configs(config_file)

        logging.basicConfig(level=self.configs["logging_level"])
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def load_configs(self, file="monitoring_config.json"):
        with open(file, "r") as f:
            return json.load(f)

    def make_config_file(self, file="monitoring_config.json"):
        configs = {}
        configs["host"] = "localhost"
        configs["port"] = 12345
        configs["logging_level"] = logging.DEBUG
        configs["poll_rate"] = 1     # second
        configs["interface_boards"] = 1
        with open(file, "w") as f:
            json.dump(configs, f, indent=4)

    def connect(self):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.connect((self.configs["host"], self.configs["port"]))

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
        for i in range(self.configs["interface_boards"]):
            package = "temperature {}".format(i)
            self.send(package)
            temperatures[i] = self.receive()
        logging.debug("Temperatures:")
        logging.debug(temperatures)
        return temperatures
    

    def get_voltages(self):
        logging.info("Getting voltage")
        voltages = {}
        for i in range(self.configs["interface_boards"]):
            package = "voltage {}".format(i)
            self.send(package)
            voltages[i] = self.receive()
        logging.debug("voltages:")
        logging.debug(voltages)
        return voltages
    
    def get_currents(self):
        logging.info("Getting current")
        currents = {}
        for i in range(self.configs["interface_boards"]):
            package = "current {}".format(i)
            self.send(package)
            currents[i] = self.receive()
        logging.debug("currents:")
        logging.debug(currents)
        return currents
    

    

def main(argv):
    config_file = None
    if len(argv) > 1:
        config_file = argv[1]
    with sepdMonitor(config_file) as monitor:
        # monitor.make_config_file()
        # sys.exit()
        logging.debug("opening monitor")
        for i in range(5):
            temperatures = monitor.get_temperatures()
            voltages = monitor.get_voltages()
            currents = monitor.get_currents()
            time.sleep(monitor.configs["poll_rate"])

if __name__ == "__main__":
    main(sys.argv)
