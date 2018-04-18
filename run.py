#!/usr/bin/env python

import logging
from daemon.station_runner import StationRunner

def run():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    station_daemon = StationRunner("/tmp/station_runner.pid")
    station_daemon.run()

if __name__ == "__main__":
    run()
