"""
Tristan Protzman
Jul 23 2023
"""

import json
import logging
import telnetlib
import functools
import multiprocessing
import subprocess

multiprocessing.set_start_method('fork')

default_timeout = 2 # seconds

"""
Applies a timeout to any functions which returns a dict
"""
def timeout(timeout):
    def decorator(func):
        def return_value(func, retval, *args, **kwargs): # Uses a dict in shared memory rather than return value
            retval.update(func(*args, **kwargs))

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logging.debug(f"Starting thread for function {func.__name__}")
            value = {}
            with multiprocessing.Manager() as manager:
                value = manager.dict()
                p = multiprocessing.Process(target=return_value, args=(func, value) + args, kwargs=kwargs)
                p.start()
                p.join(timeout)
                if p.is_alive():
                    logging.warning(f"Function {func.__name__} timed out in {timeout} seconds.  Terminating function...")
                    p.terminate()
                value = value.copy()
            return value
        return wrapper
    return decorator

@timeout(default_timeout)
def get_temperatures(crate, side):
    temperatures = {}
    offset = 0
    if side == "south":
        offset = 6
    for board in range(6):
        command = "$T{}".format(board).encode("ascii") + b"\n\r"
        logging.debug("sending {} to controller".format(command))
        crate.write(command)
        response = crate.read_until(b'>').decode()
        logging.debug("received {}".format(response))
        temperatures[board + offset] = response[:-1].split()
    return temperatures

    
@timeout(default_timeout)
def get_interface_voltages(crate, side):
    voltages = {}
    offset = 0
    if side == "south":
        offset = 6
    for board in range(6):
        command = "$U{}".format(board).encode("ascii") + b"\n\r"
        logging.debug("sending {} to controller".format(command))
        crate.write(command)
        response = crate.read_until(b'>').decode()
        logging.debug("received {}".format(response))
        response = response[:-2].split(",")
        positive_voltage = float(response[0][response[0].find("=") + 1:].strip())
        negative_voltage = float(response[1][response[1].find("=") + 1:].strip())
        bias_voltage = float(response[2][response[2].find("=") + 1:].strip())
        voltages[board + offset] = {"positive" : positive_voltage, "negative" : negative_voltage, "bias" : bias_voltage}
    return voltages

@timeout(default_timeout)
def get_interface_current(crate, side):
    currents = {}
    offset = 0
    if side == "south":
        offset = 6
    for board in range(6):
        command = "$I{}".format(board).encode("ascii") + b"\n\r"
        logging.debug("sending {} to controller".format(command))
        crate.write(command)
        response = crate.read_until(b'>').decode()
        logging.debug("received {}".format(response))
        currents[board + offset] = response[:-1].split()
    return currents

@timeout(default_timeout)
def get_lv_voltages(crate):
    voltagess = {}
    for board in (1, 2):
        command = "$V0{}".format(board).encode("ascii") + b"\n\r"
        logging.debug("sending {} to lv crate".format(command))
        crate.write(command)
        response = crate.read_until(b'>').decode()
        logging.debug("received {}".format(response))
        v = response[2:-2].split(",")
        voltagess[board] = {i : {"positive" : v[i], "negative" : v[i+8]} for i in range(8)}
    return voltagess

@timeout(default_timeout)
def get_lv_currents(crate):
    currents = {}
    for board in (1, 2):
        command = "$I0{}".format(board).encode("ascii") + b"\n\r"
        logging.debug("sending {} to lv crate".format(command))
        crate.write(command)
        response = crate.read_until(b'>').decode()
        logging.debug("received {}".format(response))
        c = response[2:-2].split(",")
        currents[board] = {i : {"positive" : c[i], "negative" : c[i+8]} for i in range(8)}
    return currents

def get_bias_status():
    bias_status = {}
    logging.debug("Getting bias crate info")
    output = subprocess.check_output("/home/phnxrc/BiasControl/sEPD_status.sh").decode()
    channel_info = [line for line in output.splitlines()]
    for channel in channel_info:
        info = channel.split()
        channel_number = info[0][3:]
        bias_status[channel_number] = {}
        bias_status[channel_number]["bias_setpoint"] = float(info[1])
        bias_status[channel_number]["current_limit"] = float(info[2])
        bias_status[channel_number]["bias_readback"] = float(info[3])
        bias_status[channel_number]["current_readback"] = float(info[4])
        bias_status[channel_number]["channel_state"] = 1 if info[6] == "on" else 0
        bias_status[channel_number]["channel_okay"] = 1 if info[7] == "Ok" else 0
    return bias_status

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

    


    def get_sEPD_metrics(self):
        timeout = 1
        temperatures = {}
        interface_voltages = {}
        interface_currents = {}
        for side in ("north", "south"):
            with telnetlib.Telnet(self.configs[f"{side}_controller_host"], self.configs[f"{side}_controller_port"], timeout) as crate:
                temperatures.update(get_temperatures(crate, side))
                interface_voltages.update(get_interface_voltages(crate, side))
                interface_currents.update(get_interface_current(crate, side))

        lv_voltages = {}
        lv_currents = {}
        with telnetlib.Telnet(self.configs["lv_host"], self.configs["lv_port"], timeout) as crate:
            lv_voltages.update(get_lv_voltages(crate))
            lv_currents.update(get_lv_currents(crate))

        bias = get_bias_status()

        response = {"temperatures" : temperatures,
                    "interface_voltages" : interface_voltages,
                    "interface_currents" : interface_currents,
                    "lv_voltages" : lv_voltages,
                    "lv_currents" : lv_currents,
                    "bias_info" : bias}
        return response
        
            


