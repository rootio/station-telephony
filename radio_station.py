# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="HP Envy"
__date__ ="$Nov 19, 2014 1:50:35 PM$"

from memory_profiler import profile
from rootio.radio.models import Station
from call_handler import CallHandler
from program_handler import ProgramHandler
import time
import threading
import json
import logging

class RadioStation(Station):
 
    def run(self):
        self.call_handler = CallHandler(self)
        self.__program_handler = ProgramHandler(self.db, self)
        self.__program_handler.run()
        while True:
            time.sleep(1)
        return
    
    def stop(self):
        self.call_handler.stop()
        self.__program_handler.stop()
        pass
 
    @profile
    def __init__(self, station_id, db, logger):
        self.id = station_id
        self.logger = logger
        self.db = db
        self.station = self.db.query(Station).filter(Station.id == station_id).one()
        self.logger.info("Starting up station {0}".format(self.station.name))
        return
