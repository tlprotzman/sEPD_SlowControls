#!/usr/bin/env python3

"""
organization

metric: supply_voltage
    labels: interface_board, rail
metric: temperature
    labels: interface_board
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

import sepd_sc_monitoring

# process input arguments
parser = argparse.ArgumentParser(
    prog='status',
    description='Prometheus Data Exporter for sPHENIX TPOT HV module',
    epilog='')
parser.add_argument('-p', '--port', default=5100,  help='Webservice port')
parser.add_argument('-l', '--limit', default=2,
                    help='Scrubbing time throttling limit in seconds')
parser.add_argument('-c', '--sepd_config', default=None, help='sEPD monitor config file')
args = parser.parse_args()

throttling_limit = float(args.limit)
print(f'Throttling request to no less than {throttling_limit} seconds')

# initialization
metric_prefix = 'sphenix_sEPD'
label_host = {}

registry = CollectorRegistry()
metrics = {}

# Host prints
print(f"Host name:        {socket.gethostname()}")
label_host[f"hostname"] = socket.gethostname()

request_counter = Counter(f'{metric_prefix}_request_counter', 'Requests processed',
                          list(label_host.keys()) + ['status'], registry=registry)
request_time = Summary(f'{metric_prefix}_requests_processing_seconds', 'Inprogress HTTP requests',
                       list(label_host.keys()), registry=registry)



monitor = sepd_sc_monitoring.sepdMonitor(args.sepd_config)
monitor.connect()


def sepd_information(verbose=False):
    # Voltage monitors
    voltages = monitor.get_voltages()
    print(voltages)
    if "voltages" not in metrics:
        metrics["voltages"] = Gauge(f'{metric_prefix}_voltages', "Interface board voltages", ["interface", "rail"], unit="V", registry=registry)
    for interface_board in voltages.keys():
        logging.debug(f"Writing for interface board {interface_board}")
        metrics["voltages"].labels(interface=interface_board, rail="positive").set(voltages[interface_board]["positive"])
        metrics["voltages"].labels(interface=interface_board, rail="negative").set(voltages[interface_board]["negative"])
        metrics["voltages"].labels(interface=interface_board, rail="bias").set(voltages[interface_board]["bias"])


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
                print('requests_metrics: Time litmit throttled....')
                request_counter.labels(status='throttled', **label_host).inc()
            else:
                # refresh all readings
                # clear metrics
                for key, metric in metrics.items():
                    metric.clear()

                # read all channel information
                sepd_information()

                requests_metrics.lastcall = time.time()
                request_counter.labels(status='updated', **label_host).inc()

        except Exception as e:
            print(f'requests_metrics: caught {type(e)}: {e}')
            request_counter.labels(status='failed', **label_host).inc()

        request_time.labels(**label_host).observe(time.time() - start_time)

    return Response(prometheus_client.generate_latest(registry), mimetype='text/plain')

requests_metrics.lastcall = time.time()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=args.port)

