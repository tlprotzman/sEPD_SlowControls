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
import telnetlib

class sepdMonitor:
    def __init__(self, config_file=None):
        if config_file is None:
            self.configs = self.load_configs()
        else:
            self.configs = self.load_configs(config_file)

        logging.basicConfig(level=self.configs["logging_level"])
        pass

    def load_configs(self, file="monitoring_config.json"):
        with open(file, "r") as f:
            return json.load(f)

    def get_temperatures(self, crate, side):
        temperatures = {}
        offset = 0
        if side == "south":
            offset = 6
        for board in range(6):
            command = "$T{}".format(board).encode("ascii") + b"\n\r"
            logging.info("sending {} to controller".format(command))
            crate.write(command)
            response = crate.read_until(b'>').decode()
            logging.info("received {}".format(response))
            temperatures[board + offset] = response[:-1].split()
        return temperatures
            
    def get_interface_voltages(self, crate, side):
        voltages = {}
        offset = 0
        if side == "south":
            offset = 6
        for board in range(6):
            command = "$U{}".format(board).encode("ascii") + b"\n\r"
            logging.info("sending {} to controller".format(command))
            crate.write(command)
            response = crate.read_until(b'>').decode()
            logging.info("received {}".format(response))
            response = response[:-2].split(",")
            positive_voltage = float(response[0][response[0].find("=") + 1:].strip())
            negative_voltage = float(response[1][response[1].find("=") + 1:].strip())
            bias_voltage = float(response[2][response[2].find("=") + 1:].strip())
            voltages[board + offset] = {"positive" : positive_voltage, "negative" : negative_voltage, "bias" : bias_voltage}
        return voltages

    def get_interface_current(self, crate, side):
        currents = {}
        offset = 0
        if side == "south":
            offset = 6
        for board in range(6):
            command = "$I{}".format(board).encode("ascii") + b"\n\r"
            logging.info("sending {} to controller".format(command))
            crate.write(command)
            response = crate.read_until(b'>').decode()
            logging.info("received {}".format(response))
            currents[board + offset] = response[:-1].split()
        return currents

    def get_lv_voltages(self, crate):
        voltagess = {}
        for board in (1, 2):
            command = "$V0{}".format(board).encode("ascii") + b"\n\r"
            logging.info("sending {} to lv crate".format(command))
            crate.write(command)
            response = crate.read_until(b'>').decode()
            logging.info("received {}".format(response))
            v = response[2:-2].split(",")
            voltagess[board] = {i : {"positive" : v[i], "negative" : v[i+8]} for i in range(8)}
        return voltagess

    def get_lv_currents(self, crate):
        currents = {}
        for board in (1, 2):
            command = "$I0{}".format(board).encode("ascii") + b"\n\r"
            logging.info("sending {} to lv crate".format(command))
            crate.write(command)
            response = crate.read_until(b'>').decode()
            logging.info("received {}".format(response))
            c = response[2:-2].split(",")
            currents[board] = {i : {"positive" : c[i], "negative" : c[i+8]} for i in range(8)}
        return currents


    def get_sEPD_metrics(self):
        timeout = 5
        temperatures = {}
        interface_voltages = {}
        interface_currents = {}
        for side in ("north", "south"):
            with telnetlib.Telnet(self.configs[f"{side}_controller_host"], self.configs[f"{side}_controller_port"], timeout) as crate:
                temperatures.update(self.get_temperatures(crate, side))
                interface_voltages.update(self.get_interface_voltages(crate, side))
                interface_currents.update(self.get_interface_current(crate, side))

        lv_voltages = {}
        lv_currents = {}
        with telnetlib.Telnet(self.configs["lv_host"], self.configs["lv_port"], timeout) as crate:
            lv_voltages.update(self.get_lv_voltages(crate))
            lv_currents.update(self.get_lv_currents(crate))

        response = {"temperatures" : temperatures,
                    "interface_voltages" : interface_voltages,
                    "interface_currents" : interface_currents,
                    "lv_voltages" : lv_voltages,
                    "lv_currents" : lv_currents}
        return response
        
            


