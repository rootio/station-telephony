import json
import socket
import threading
from time import sleep
from datetime import date, datetime, timedelta, time

import dateutil.tz
import pytz
from pytz import timezone
from apscheduler.scheduler import Scheduler
from rootio.config import DefaultConfig
from rootio.radio.models import ScheduledProgram
from sqlalchemy import text

from radio_program import RadioProgram


class ProgramHandler:

    def __init__(self, db, radio_station):
        self.__db = db
        self.__radio_station = radio_station
        self.__scheduler = None
        self.__scheduled_jobs = None
        self.__start_listeners()
        self.__radio_station.logger.info("Done initialising ProgramHandler for {0}".format(radio_station.station.name))

    def run(self):
        self.run_today_schedule()

    def __prepare_schedule(self):
        self.__load_programs()
        self.__scheduler = Scheduler()
        self.__scheduled_jobs = dict()

    def run_today_schedule(self):
        self.__prepare_schedule()
        self.__scheduler.start()
        self.__schedule_programs()
        self.__schedule_next_day_scheduler()
        print self.__scheduler.get_jobs()

    def stop(self):
        self.__stop_program()
        # any clean up goes here
        # unschedule stuff

    def __schedule_next_day_scheduler(self):
        #TODO: make this safe for differebt timezones!
        base_date = date.today() + timedelta(1,0)
        tomorrow_date = datetime.combine(base_date, time())
        #add the timezone offset
        tomorrow_date = tomorrow_date + timedelta(0, timezone(self.__radio_station.station.timezone).utcoffset(datetime.now()).seconds)
        self.__scheduler.add_date_job(getattr(self, 'run_today_schedule'), tomorrow_date) #schedule the scheduler to reload at midnight 

    def __schedule_programs(self):
        for scheduled_program in self.__scheduled_programs:
            if not self.__is_program_expired(scheduled_program):
                self.__add_scheduled_job(scheduled_program)
                self.__radio_station.logger.info(
                    "Scheduled program {0} for station {1} starting at {2}".format(scheduled_program.program.name,
                                                                                   self.__radio_station.station.name,
                                                                                   scheduled_program.start))
        return

    def __add_scheduled_job(self, scheduled_program):
        program = RadioProgram(self.__db, scheduled_program, self.__radio_station)
        scheduled_job = self.__scheduler.add_date_job(getattr(program, 'start'),
                                                      self.__get_program_start_time(scheduled_program).replace(
                                                          tzinfo=None))
        self.__scheduled_jobs[scheduled_program.id] = scheduled_job

    def __delete_scheduled_job(self, index):
        if index in self.__scheduled_jobs:
            self.__scheduler.unschedule_job(self.__scheduled_jobs[index])
            del self.__scheduled_jobs[index]

    def __stop_program(self):
        #self.__running_program.stop()
        return

    def __run_program(self):
        #self.__running_program.run()
        return

    def __load_programs(self):
        self.__scheduled_programs = self.__db.query(ScheduledProgram).filter(
            ScheduledProgram.station_id == self.__radio_station.id).filter(text("date(start at TIME ZONE 'UTC') = current_date at TIME ZONE 'UTC'")).filter(
            ScheduledProgram.deleted == False).all()
        self.__radio_station.logger.info("Loaded programs for {0}".format(self.__radio_station.station.name))

    def __load_program(self, id):
        return self.__db.query(ScheduledProgram).filter(ScheduledProgram.id == id).first()

    def __start_listeners(self):
        t = threading.Thread(target=self.__listen_for_scheduling_changes,
                             args=(DefaultConfig.SCHEDULE_EVENTS_SERVER_IP, DefaultConfig.SCHEDULE_EVENTS_SERVER_PORT))
        t.start()

    def __listen_for_scheduling_changes(self, ip, port):
        sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr = (ip, port)
        
         #It may not be possible to connect after restart, TIME_WAIT could come into play etc. Anyway, keep trying
        connected = False
        while not connected:
            try:         
                sck.connect(addr)
                connected = True
            except:
                self.__radio_station.logger.error("Could not connect to server, retrying in 30 ...")
                sleep(30)
        sck.send(json.dumps({'station':self.__radio_station.id, 'action':'register'}))

        while True:
            data = sck.recv(1024)
            try:
                event = json.loads(data)
                if event["action"] == "delete":
                    self.__delete_scheduled_job(event["id"])
                    self.__radio_station.logger.info("Scheduled program with id {0} has been deleted".format(event["id"]))
                elif event["action"] == "add":
                    scheduled_program = self.__load_program(event["id"])
                    if not self.__is_program_expired(scheduled_program):
                        self.__add_scheduled_job(scheduled_program)
                        self.__radio_station.logger.info(
                            "Scheduled program with id {0} has been added at time {1}".format(event["id"],
                                                                                          scheduled_program.start))
                elif event["action"] == "update":
                    self.__delete_scheduled_job(event["id"])
                    scheduled_program = self.__load_program(event["id"])
                    if not self.__is_program_expired(scheduled_program, scheduled_program.program.duration):
                        self.__add_scheduled_job(scheduled_program)
                        self.__radio_station.logger.info(
                            "Scheduled program with id {0} has been moved to start at time {1}".format(event["id"],
                                                                                                 scheduled_program.start))
            except:
                pass #Most probably a JSON parse error
 

    """
    Gets the program to run from the current list of programs that are lined up for the day
    """

    def __get_current_program(self):
        for program in self.__scheduled_programs:
            if not self.__is_program_expired(program):
                return program

    """
    Returns whether or not the time for a particular program has passed
    """

    def __is_program_expired(self, scheduled_program):
        now = pytz.utc.localize(datetime.utcnow())
        return (scheduled_program.start + scheduled_program.program.duration) < (now + timedelta(minutes=1))

    def __get_program_start_time(self, scheduled_program):
        now = datetime.now(dateutil.tz.tzlocal())
        if scheduled_program.start < now:  # Time at which program begins is already past
            return now + timedelta(seconds=5)  # 5 second scheduling allowance
        else:
            return scheduled_program.start + timedelta(seconds=5)  # 5 second scheduling allowance
