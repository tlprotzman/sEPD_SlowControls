#!/usr/bin/env python3

"""
Tristan Protzman 
tlprotzman@gmail.com

TODO:
* Get bias crate status
* Add timeout to telnet commands
* Add mapping from interface boards -> sector and channel -> tile
"""

import argparse
import ctypes
from flask import Response, Flask, request, render_template_string
import json
import prometheus_client
from prometheus_client import CollectorRegistry, Gauge, Info, Counter, Summary
import re
import socket
import time
from threading import Lock
import sys
import logging
logging.basicConfig(level=logging.INFO)
import sepd_sc_monitoring

# process input arguments
parser = argparse.ArgumentParser(
    prog='status',
    description='Prometheus Data Exporter for sPHENIX sEPD Controls',
    epilog='')
parser.add_argument('-p', '--port', default=5100,  help='Webservice port')
parser.add_argument('-l', '--limit', default=1,
                    help='Scrubbing time throttling limit in seconds')
parser.add_argument('-c', '--sepd_config', default=None, help='sEPD monitor config file')
args = parser.parse_args()

throttling_limit = float(args.limit)
logging.info(f'Throttling request to no less than {throttling_limit} seconds')

# initialization
metric_prefix = 'sphenix_sEPD'
label_host = {}

registry = CollectorRegistry()
metrics = {}

# Host prints
logging.info(f"Host name:        {socket.gethostname()}")
label_host[f"hostname"] = socket.gethostname()

request_counter = Counter(f'{metric_prefix}_request_counter', 'Requests processed',
                          list(label_host.keys()) + ['status'], registry=registry)
request_time = Summary(f'{metric_prefix}_requests_processing_seconds', 'Inprogress HTTP requests',
                       list(label_host.keys()), registry=registry)



monitor = sepd_sc_monitoring.sepdMonitor(args.sepd_config)



def sepd_information(verbose=False):
    # Voltage monitors
    logging.debug("getting voltages")
    all_metrics = monitor.get_sEPD_metrics()
    logging.debug(json.dumps(all_metrics, sort_keys=True, indent=4))

    """
    INTERFACE BOARD METRICS
    """
    temperatures = all_metrics["temperatures"]
    if "temperatures" not in metrics.keys():
        metrics["temperatures"] = Gauge(f'{metric_prefix}_temperatures', "Interface board temperatures", ["side", "sector", "tile"], unit="C", registry=registry)
    for interface_board in temperatures.keys():
        for i, temp in enumerate(temperatures[interface_board]):
            side, sector, tile = monitor.IB_to_tile[int(interface_board)][i]
            
            if float(temp) < 0: # means interface board is off
                continue
            side = "north" if side == 0 else "south"
            metrics["temperatures"].labels(side=side, sector=sector, tile=tile).set(temp)

    voltages = all_metrics["interface_voltages"]
    if "voltages" not in metrics.keys():
        metrics["voltages"] = Gauge(f'{metric_prefix}_voltages', "Interface board voltages", ["side", "interface", "rail"], unit="V", registry=registry)
    for interface_board in voltages.keys():
        logging.debug(f"Writing for interface board {interface_board}")
        if float(voltages[interface_board]["positive"]) > 12:
            continue # means interface board is off
        side = "north" if monitor.IB_to_tile[int(interface_board)][0][0] == 0 else "south"
        interface_board = interface_board % 6
        metrics["voltages"].labels(side=side, interface=int(interface_board), rail="positive").set(voltages[interface_board]["positive"])
        metrics["voltages"].labels(side=side, interface=int(interface_board), rail="negative").set(voltages[interface_board]["negative"])
        metrics["voltages"].labels(side=side, interface=int(interface_board), rail="bias").set(voltages[interface_board]["bias"])

    currents = all_metrics["interface_currents"]
    if "currents" not in metrics.keys():
        metrics["currents"] = Gauge(f'{metric_prefix}_currents', "SiPM Currents", ["side", "sector", "tile"], unit="uA", registry=registry)
    for interface_board in currents.keys():
        for i, current in enumerate(currents[interface_board]):
            side, sector, tile = monitor.IB_to_tile[int(interface_board)][i]
            if float(current) > 2045: # means interface board is off
                continue
            side = "north" if side == 0 else "south"
            metrics["currents"].labels(side=side, sector=sector, tile=tile).set(current)

    """
    LOW VOLTAGE CRATE METRICS
    """
    lv_voltages = all_metrics["lv_voltages"]
    if "lv_voltages" not in metrics.keys():
        metrics["lv_voltages"] = Gauge(f"{metric_prefix}_lv_voltages", "LV crate voltages", ["board", "channel", "rail"], unit="V", registry=registry)
    for interface_board in lv_voltages.keys():
        for channel in lv_voltages[interface_board]:
            metrics["lv_voltages"].labels(board=int(interface_board), channel=int(channel), rail="positive").set(lv_voltages[interface_board][channel]["positive"])
            metrics["lv_voltages"].labels(board=int(interface_board), channel=int(channel), rail="negative").set(lv_voltages[interface_board][channel]["negative"])

    lv_currents = all_metrics["lv_currents"]
    if "lv_currents" not in metrics.keys():
        metrics["lv_currents"] = Gauge(f"{metric_prefix}_lv_currents", "LV crate currents", ["board", "channel", "rail"], unit="A", registry=registry)
    for interface_board in lv_currents.keys():
        for channel in lv_currents[interface_board]:
            metrics["lv_currents"].labels(board=int(interface_board), channel=int(channel), rail="positive").set(lv_currents[interface_board][channel]["positive"])
            metrics["lv_currents"].labels(board=int(interface_board), channel=int(channel), rail="negative").set(lv_currents[interface_board][channel]["negative"])


    """
    BIAS CRATE METRICS
    """
    bias_info = all_metrics["bias_info"]
    bias_gauges = {"bias_setpoint" : {"name" : "Bias Setpoint", "unit" : "V"},
                   "bias_readback" : {"name" : "Bias Readback", "unit" : "V"},
                   "current_limit" : {"name" : "Current Trip Limit", "unit" : "uA"},
                   "current_readback" : {"name" : "Current Readback", "unit" : "uA"},
                   "channel_state" : {"name" : "Channel State", "unit" : ""},
                   "channel_okay" : {"name" : "Channel Okay", "unit" : ""}}
    for key in bias_gauges.keys():
        if key not in metrics.keys():
            metrics[key] = Gauge(f"{metric_prefix}_{key}", bias_gauges[key]["name"], ["channel"], unit=bias_gauges[key]["unit"], registry=registry)
    for channel in bias_info.keys():
        for metric in bias_gauges.keys():
            metrics[metric].labels(channel=channel).set(bias_info[channel][metric])
    
# web service
app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string("""
<h1>Prometheus Data Exporter for sPHENIX EPD Slow Controls Values</h1>
<p>Fetch metrics at <a href="./metrics">./metrics</a>.</p>
""")

requests_metrics_lock = Lock()

@app.route("/metrics")
# @request_time.labels(**label_host).time() # did not work under python3.7
def requests_metrics():

    request_counter.labels(status='incoming', **label_host).inc()

    with requests_metrics_lock:

        start_time = time.time()

        try:
            if (time.time() - requests_metrics.lastcall < throttling_limit):
                logging.warning('requests_metrics: Time litmit throttled....')
                request_counter.labels(status='throttled', **label_host).inc()
            else:
                logging.info(f'starting request calls at {time.time()}')
                # refresh all readings
                # clear metrics
                for key, metric in metrics.items():
                    metric.clear()

                # read all channel information
                sepd_information()

                requests_metrics.lastcall = time.time()
                request_counter.labels(status='updated', **label_host).inc()
                logging.info(f'ended request calls at {time.time()}')

        except Exception as e:
            logging.error(f'requests_metrics: caught {type(e)}: {e}')
            request_counter.labels(status='failed', **label_host).inc()

        request_time.labels(**label_host).observe(time.time() - start_time)

    return Response(prometheus_client.generate_latest(registry), mimetype='text/plain')

requests_metrics.lastcall = time.time()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=args.port)

