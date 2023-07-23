"""
sEPD Slow Controls Server
Tristan Protzman
20 Jul 2023
"""

HOST = "localhost"
PORT = 12345

# LV_ADDRESS = ("10.20.34.136", "9760")
LV_ADDRESS = ("localhost", "5001")
# CONTROLLER_ADDRESS = ("10.20.34.98", "9760")
CONTROLLER_ADDRESS = ("localhost", "5000")

import telnetlib
import socketserver
import logging
import pickle
import sys
import struct


class sepdServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, address, handler):
        socketserver.TCPServer.__init__(self, address, handler)
        self.testvalue = 123

    def __enter__(self):
        logging.info("entering context manager")
        self.lv_telnet = self.openTelnetConnection(*LV_ADDRESS)
        self.controller_telnet = self.openTelnetConnection(*CONTROLLER_ADDRESS)
        return socketserver.TCPServer.__enter__(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.info("exiting context manager")
        self.lv_telnet.close()
        self.controller_telnet.close()
        return socketserver.TCPServer.__exit__(self, exc_type, exc_val, exc_tb)

    def openTelnetConnection(self, host, port):
        try:
            logging.info("Connecting to {}:{} via telnet".format(host, port))
            tn = telnetlib.Telnet(host, port, timeout=5)
            logging.info("Opened connection!")
            return tn
        except Exception as e:
            logging.critical("Could not open telnet connection: Error {}".format(e))

    def shutdown_server(self):
        self._BaseServer__shutdown_request = True

    def query_controller_voltages(self, board):
        command = "$U{}".format(board).encode("ascii") + b"\n\r"
        logging.info("sending {} to controller".format(command))
        self.controller_telnet.write(command)
        response = self.controller_telnet.read_until(b'>').decode()
        logging.info("received {}".format(response))
        response = response[:-2].split(",")
        positive_voltage = float(response[0][response[0].find("=") + 1:].strip())
        negative_voltage = float(response[1][response[1].find("=") + 1:].strip())
        bias_voltage = float(response[2][response[2].find("=") + 1:].strip())
        return {"positive" : positive_voltage, "negative" : negative_voltage, "bias" : bias_voltage}
    
    def query_controller_temperature(self, board):
        command = "$T{}".format(board).encode("ascii") + b"\n\r"
        logging.info("sending {} to controller".format(command))
        self.controller_telnet.write(command)
        response = self.controller_telnet.read_until(b'>').decode()
        logging.info("received {}".format(response))
        temperatures = response[:-1].split()
        return temperatures
    

    def query_sipm_current(self, board):
        command = "$I{}".format(board).encode("ascii") + b"\n\r"
        logging.info("sending {} to controller".format(command))
        self.controller_telnet.write(command)
        response = self.controller_telnet.read_until(b'>').decode()
        logging.info("received {}".format(response))
        currents = response[:-1].split()
        return currents


class sepdServerHandler(socketserver.StreamRequestHandler):
    def handle(self):
        for data in self.rfile:
            try:
                # data = self.rfile.readline()
                logging.debug("received {} bytes".format(len(data)))
                data = [d.decode() for d in data.strip().split()]
                logging.info("received message {}".format(data))
                package = None
                if data[0].lower() in ("h", "?", "help"):
                    package  = "Welcome to the sEPD control server\n"
                    package += "If something is broken, check the wiki (https://wiki.sphenix.bnl.gov/index.php/SPHENIX_Event_Plane_Detector) "
                    package += "and then contact Tristan (570-647-9724) if you can't figure it out\n\n"
                    package += "Usage:\n"
                    package += "\ttemperature x\t\t Reads the temperatures of interface board x\n"
                    package += "\tvoltage x\t\t Reads the voltages of interface board x\n"
                    package += "\tcurrent x\t\t Reads the SiPM currents of interface board x\n"

                if data[0] == "temperature":
                    try:
                        card = int(data[1])
                        package = self.server.query_controller_temperature(card)
                    except Exception as e:
                        package = "Specify interface board number: {}".format(e)
                        
                elif data[0] == "voltage":
                    try:
                        card = int(data[1])
                        package = self.server.query_controller_voltages(card)
                    except Exception as e:
                        package = "Specify interface board number: {}".format(e)

                elif data[0] == "current":
                    try:
                        card = int(data[1])
                        package = self.server.query_sipm_current(card)
                    except Exception as e:
                        package = "Specify interface board number: {}".format(e)

                elif data[0] == "shutdown":
                    self.server.shutdown()

                # print(data)
                logging.info("Package to reply with is {}".format(package))
                package = pickle.dumps(package)
                logging.info("Package is {} bytes".format(len(package)))
                self.wfile.write(struct.pack(">I", len(package)))
                self.wfile.write(package)
            except Exception as e:
                logging.warning("Handler exception: {}".format(e))

        





logging.basicConfig(level=logging.DEBUG)
with sepdServer((HOST, PORT), sepdServerHandler) as server:
    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
