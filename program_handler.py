import datetime
# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="HP Envy"
__date__ ="$Nov 19, 2014 2:17:51 PM$"

from memory_profiler import profile
from rootio.radio.models import ScheduledProgram, Program
import dateutil.tz
from datetime import datetime, timedelta
from radio_program import RadioProgram
import pytz
from apscheduler.scheduler import Scheduler
from sqlalchemy import text

class ProgramHandler:
   
    @profile 
    def __init__(self, db, radio_station):
        self.__db = db
        self.__radio_station = radio_station
        self.__load_programs()
        self.__jobs = dict()
        self.__scheduler = Scheduler()
        self.__radio_station.logger.info("Done initing ProgramHandler for {0}".format(radio_station.station.name))
 
    @profile
    def run(self):
        self.__scheduler.start()
        self.__schedule_programs()
        #self.__scheduler.start()
    
    def stop(self):
        self.__stop_program()
        #any clean up goes here
    
    @profile
    def __schedule_programs(self):
        for scheduled_program in self.__scheduled_programs:#throw all the jobs into AP scheduler and have it rain down alerts
            if not self.__is_program_expired(scheduled_program, scheduled_program.program.duration):
                try:
                    program = RadioProgram(self.__db, scheduled_program, self.__radio_station)
                    self.__radio_station.logger.info("Delay seconds is {0}".format(int(scheduled_program.program.duration.total_seconds())))
                    scheduled_job = self.__scheduler.add_date_job(getattr(program,'start'), self.__get_program_start_time(scheduled_program).replace(tzinfo=None))
                    self.__scheduled_jobs[scheduled_program.id] = scheduled_job #Keep reference in case you need to update/delete jobs in the future.
                    self.__radio_station.logger.info("Scheduled program {0} for station {1} starting at {2}".format(scheduled_program.program.name, self.__radio_station.station.name, scheduled_program.start))
                except Exception, e:
                    self.__radio_station.logger.info(str(e))
        return 

    def __delete_job(self, index):
        if index in self.__scheduled_jobs:
            self.__scheduler.unschedule_job(self.__scheduled_jobs[index])
            del self.__scheduled_jobs[index]

    def __stop_program(self):
        __running_program.stop()
        return
    
    def __run_program(self):
        __running_program.run()
        return
    
    def __load_programs(self):
        self.__scheduled_programs = self.__db.query(ScheduledProgram).filter(ScheduledProgram.station_id == self.__radio_station.id).filter(text("date(start) = current_date")).filter(ScheduledProgram.deleted==False).all()
        self.__radio_station.logger.info("Loaded programs for {0}".format(self.__radio_station.station.name))
    
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
    def __is_program_expired(self, scheduled_program, program_duration):
        now = pytz.utc.localize(datetime.utcnow())
        return (scheduled_program.start + scheduled_program.program.duration) < (now + timedelta(minutes=1))

    def __get_program_start_time(self, scheduled_program):
        now  = datetime.now(dateutil.tz.tzlocal())
        if scheduled_program.start < now: #Time at which program begins is already past
            return now + timedelta(seconds=5) #5 second scheduling allowance
        else:
            return scheduled_program.start + timedelta(seconds=5) #5 second scheduling allowance    
