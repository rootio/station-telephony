# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="HP Envy"
__date__ ="$Nov 20, 2014 3:01:00 PM$"

import pytz
import json
from outcall_action import OutcallAction
from jingle_action import JingleAction
from media_action import MediaAction
from tts_action import TTSAction
from interlude_action import InterludeAction
from datetime import datetime, timedelta
from apscheduler.scheduler import Scheduler
from rootio_mailer.rootio_mail_message import RootIOMailMessage

class RadioProgram:
    
    def __init__(self, db, program, radio_station):
        self.__program_actions = []
        self.id = program.id
        self.__db = db
        self.name = program.id
        self.__program = program
        self.radio_station = radio_station
        self.__scheduler = Scheduler()
        self.__running_action = None
        self.__rootio_mail_message = RootIOMailMessage()
        return
        
    '''
    Starts a station program and does the necessary preparations
    '''
    def start(self):
        self.__load_program_actions()
        self.__schedule_program_actions()
        self.__scheduler.start()
        return
    
    '''
    Load the definition of components of the program from a JSON definition
    '''
    def __load_program_actions(self):
        print self.__program.program.description
        data = json.loads(self.__program.program.description)
        self.radio_station.logger.info(data)
        for category in data:
            self.radio_station.logger.info(category)
            if category == "Jingle":
                for action in data[category]:
                    self.__program_actions.append(JingleAction(action["argument"], action["start_time"], action["duration"], action["is_streamed"], self, action["hangup_on_complete"]))
                    print "Jingle scheduled to start at " + str(record["start_time"])
            if category == "Media":
                for action in data[category]:
                    self.__program_actions.append(MediaAction(action["argument"], action["start_time"], action["duration"], action["is_streamed"], self, action["hangup_on_complete"]))
                    self.radio_station.logger.info("Media Scheduled to start at {0}".format(str(action["start_time"])))
            if category == "tts":
                self.radio_station.logger.info('is tts')
                for action in data[category]:
                    self.radio_station.logger.info('action')
                    self.__program_actions.append(TTSAction(action["argument"],action["start_time"], action["duration"], action["is_streamed"], self, action["hangup_on_complete"]))
                    self.radio_station.logger.info("TTS Scheduled to start at {0}".format(str(action["start_time"])))
            if category == "Interlude":
                for action in data[category]:
                    self.__program_actions.append(InterludeAction(action["argument"], action["start_time"], action["duration"], action["is_streamed"], self, action["hangup_on_complete"]))
                    print "Interlude Scheduled to start at " + str(action["start_time"])
            if category == "Stream":
                #self.__program_actions.add(JingleAction(j['argument']))
                print "Stream would have started here"
            if category == "Music":
                #self.__program_actions.add(MediaAction(j['argument']))
                print "This would have started here"
            if category == "Outcall":
                for action in data[category]:
                    print "Call to host scheduled to start at " + str(action["start_time"])
                    self.__program_actions.append(OutcallAction(action['argument'],action["start_time"], action['duration'], action['is_streamed'], action['warning_time'],self, action["hangup_on_complete"]) )    
        return
    
    '''
    Schedule the actions of a particular program for playback within the program
    '''
    def __schedule_program_actions(self):
        for program_action in self.__program_actions:
            self.__scheduler.add_date_job(getattr(program_action,'start'), self.__get_start_datetime(program_action.start_time).replace(tzinfo=None), misfire_grace_time=program_action.duration)
         
    def set_running_action(self, running_action):
        if not self.__running_action == None:
            self.__running_action.stop()#clean up any stuff that is not necessary anymore
        self.__running_action = running_action

    def log_program_activity(self, program_activity):
        self.__rootio_mail_message.append_to_body('%s %s' % (datetime.now().strftime('%y-%m-%d %H:%M:%S'),program_activity))

    def notify_program_action_stopped(self, program_action):
        if program_action in self.__program_actions:
            self.__program_actions.remove(program_action)
            #if len(self.__program_actions) == 0: #all program actions have run
                #self.__send_program_summary()

    def __send_program_summary(self):
        self.__rootio_mail_message.set_subject('[%s] %s ' % (self.radio_station.station.name, self.__program.program.name))
        self.__rootio_mail_message.set_from('RootIO')#This will come from DB in future
        self.__rootio_mail_message.add_to_address('jude19love@gmail.com')#this wil come from DB in future
        self.__rootio_mail_message.add_to_address('choowilly@gmail.com')#This will also come from DB
        self.__rootio_mail_message.send_message()

    '''
    Get the time at which to schedule the program action to start
    '''        
    def __get_start_datetime(self, time_part):
        now  = pytz.utc.localize(datetime.utcnow())
        t = datetime.strptime(time_part, "%H:%M:%S")
        time_delta = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        return now + time_delta + timedelta(seconds=2) #2 second scheduling allowance
    
