#!/usr/bin/env python

from daemon.station_runner import StationRunner

def run():
    station_daemon = StationRunner("/tmp/station_runner.pid")
    station_daemon.run()

if __name__ == "__main__":
    run()
