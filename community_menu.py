#import the necessary stuff here
import urllib
from datetime import datetime, timedelta
from time import mktime

import feedparser
from rootio.config import *
from rootio.content.models import CommunityContent
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
import re
import os
from time import sleep
from datetime import datetime, timedelta

class CommunityMenu:

    def __init__(self, radio_station):
        #Load GWs for ths station
        #register listeners for incoming calls on those extensions, basically parked.
        self.__category_id = None
        self.__num_days = None
        self.__recorded_file = None
        self.__post_recording_option = None
        self.__call = None
        self.__radio_station = radio_station
        self.__gateway = None
        self.__accumulated_dtmf = None
        self.__last_speak_time = None
        self.__is_speaking = False
        self.__is_playing_audio = False
        self.__db = self.__get_db_connection()
        self.__menu = self.__get_community_menu() #is a 1:1 mapping between the two tables
        self.__start_listener()

    def __get_db_connection(self):
        engine = create_engine(DefaultConfig.SQLALCHEMY_DATABASE_URI)
        return sessionmaker(bind=engine)()

    def __start_listener(self):
        self.__gateway = self.__get_gateway_used()
        if self.__gateway != None:
            self.__radio_station.call_handler.register_for_incoming_calls(self, True)
            self.__radio_station.call_handler.register_for_call_hangup(self, str(self.__gateway))
            self.__radio_station.call_handler.register_for_media_playback_stop(self, str(self.__gateway))
        self.__radio_station.call_handler.register_for_media_playback_start(self, str(self.__gateway))

    def __get_community_menu(self):
        if len(self.__radio_station.station.community_menu) > 0:
            return self.__radio_station.station.community_menu[0]
        else:
            return None
   
    def __get_gateway_used(self): #this retrieves the extension that listens for calls for ads and announcements
        gws = []
        for gw in self.__radio_station.station.incoming_gateways:
            gws.append(gw.number_bottom)
        gws.sort()

        if len(gws) > 0:
            return gws[0]
        else:
            return None

    def __finalize(self):
        #hangup, clean variables, deregister for DTMF
        try:
            self.__radio_station.call_handler.hangup(self.__call['Channel-Call-UUID'])
        except:
            pass 
        self.__radio_station.call_handler.deregister_for_incoming_dtmf(str(self.__gateway))
        #self.__radio_station.call_handler.deregister_for_incoming_calls(self)
        #self.__radio_station.call_handler.deregister_for_call_hangup(str(self.__gateway))
        #self.__radio_station.call_handler.deregister_for_media_playback_stop(str(self.__gateway))
        #self.__radio_station.call_handler.deregister_for_media_playback_start(str(self.__gateway))

        #self.__category_id = None
        self.__num_days = None
        self.__recorded_file = None
        self.__post_recording_option = None
        self.__call = None
        self.__accumulated_dtmf = None
        self.__last_speak_time = None
        self.__is_speaking = False
        self.__is_playing_audio = False

    
    def notify_incoming_call(self, call_json):
        self.__call = call_json
        self.__radio_station.call_handler.bridge_incoming_call(call_json['Channel-Call-UUID'], "12")
        self.__start(self.__call['Channel-Call-UUID']) 
 
    def notify_incoming_dtmf(self, event_json):
        if self.__accumulated_dtmf == None:
            self.__accumulated_dtmf = event_json["DTMF-Digit"]
        else:
            self.__accumulated_dtmf = self.__accumulated_dtmf + event_json["DTMF-Digit"]
    
    def notify_speak_stop(self, event_json):
        self.__last_speak_time = datetime.now()
        self.__is_speaking = False

    def notify_speak_start(self, event_json):
        self.__is_speaking = True        
 
    def notify_media_play_stop(self, event_json):
        self.__is_playing_audio = False

    def notify_media_play_start(self, event_json):
        self.__is_playing_audio = True
    
    def notify_call_hangup(self, event_json):
        self.__finalize()

    '''
    This plays an audio prompt and then gets the digits entered.
    Will wait for a maximum of timeout_secs to return the entered DTMF digits
    '''
    def __play_and_get_max_dtmf(self, call_uuid, audio_prompt, max_int, timeout_secs, num_attempts):
        attempts = 0
        while attempts < num_attempts:
            self.__play(call_uuid, audio_prompt)
            self.__radio_station.call_handler.register_for_incoming_dtmf(self, self.__gateway)
            sleep(timeout_secs)
            #self.__radio_station.call_handler.deregister_for_incoming_dtmf(self.__gateway)
            if self.__accumulated_dtmf != None and int(self.__accumulated_dtmf) <= max_int:
                dtmf = self.__accumulated_dtmf
                self.__accumulated_dtmf = None
                return dtmf
            attempts = attempts + 1 
        self.__accumulated_dtmf = None
        return None    

    def __play_and_get_specific_dtmf(self, call_uuid, audio_prompt, allowed_digits, timeout_secs, num_attempts):
        attempts = 0
        
        while attempts < num_attempts:
            self.__play(call_uuid, audio_prompt)
            self.__radio_station.call_handler.register_for_incoming_dtmf(self, str(self.__gateway))
            
            start_time = datetime.now()
            while datetime.now() < start_time +timedelta(0, timeout_secs) and self.__accumulated_dtmf == None:
                pass #wait

            #self.__radio_station.call_handler.deregister_for_incoming_dtmf(str(self.__gateway))
            if self.__accumulated_dtmf != None and self.__accumulated_dtmf in allowed_digits:
                dtmf = self.__accumulated_dtmf
                self.__accumulated_dtmf = None
                return dtmf
            attempts = attempts + 1
        self.__accumulated_dtmf = None
        return None

    def __play(self, call_uuid, audio_file):
        self.__radio_station.call_handler.play(call_uuid, audio_file)
        self.__is_playing_audio = True #Not safe - Audio might throw an error
        self.__wait_on_audio()

    def __record_audio_file(self, call_uuid, audio_path):
        self.__radio_station.call_handler.record_call(call_uuid, audio_path)

    def __stop_record_audio_file(self, call_uuid, audio_path):
        self.__radio_station.call_handler.stop_record_call(call_uuid,  audio_path)

    def __save_message(self, filename, originator, date_recorded, duration, message_type, valid_until, station):
        cm = CommunityContent()
        cm.date_created = date_recorded
        cm.originator = originator
        cm.duration = duration
        cm.type_code = message_type
        cm.valid_until = valid_until
        cm.message = filename
        cm.station = station
        db_session = self.__db.object_session(cm)
        db_session._model_changes = {}
        db_session.add(cm)
        db_session.commit()
    
    def __wait_on_audio(self): #commands issued after play of audio are executed while FS is playing audio...
        while self.__is_playing_audio:
            pass 
    
    def __start(self, call_uuid): #called by the call handler upon receiving a call on the extension for which this is registered
        self.__radio_station.call_handler.register_for_media_playback_stop(self, str(self.__gateway))
        self.__radio_station.call_handler.register_for_media_playback_start(self, str(self.__gateway))    
        
        self.__play(call_uuid, os.path.join(DefaultConfig.CONTENT_DIR, self.__menu.welcome_message))

        #get the category of the message being left
        self.__category_id = self.__play_and_get_specific_dtmf(call_uuid, os.path.join(DefaultConfig.CONTENT_DIR, self.__menu.message_type_prompt), ["1","2","3"], 15, 3)
        if self.__category_id == None:
            self.__finalize()
            return
        
        #get the number of days for which valid
        self.__num_days = self.__play_and_get_max_dtmf(call_uuid, os.path.join(DefaultConfig.CONTENT_DIR, self.__menu.days_prompt), 14, 15, 3)
        if self.__num_days == None:
            self.__finalize()
            return

        #instruct the person to record their message
        self.__play(call_uuid, os.path.join(DefaultConfig.CONTENT_DIR, self.__menu.record_prompt))
        filename = "{0}_{1}_recording.wav".format(self.__call['Caller-ANI'], datetime.strftime(datetime.now(), "%Y%M%d%H%M%S"))
        audio_path = os.path.join(DefaultConfig.CONTENT_DIR, "community-content", str(self.__radio_station.station.id), self.__category_id, filename)
        self.__record_audio_file(call_uuid, audio_path)
        self.__radio_station.call_handler.register_for_speak_stop(self, str(self.__gateway))
        self.__radio_station.call_handler.register_for_speak_start(self, str(self.__gateway))
        self.__radio_station.call_handler.register_for_incoming_dtmf(self, str(self.__gateway))
        
        self.__recording_start_time = datetime.now()
        self.__is_speaking = True
        self.__last_speak_time = datetime.now()
        while (self.__is_speaking and self.__last_speak_time + timedelta(0, 30) > datetime.now()) and not (self.__accumulated_dtmf != None and "#" in self.__accumulated_dtmf): #duration of 30 sec, # key or silence of 5 seconds will result in end of recording
            pass
        self.__accumulated_dtmf = None        
        self.__stop_record_audio_file(call_uuid, audio_path)
        self.__radio_station.call_handler.deregister_for_speak_stop(str(self.__gateway))
        self.__radio_station.call_handler.deregister_for_speak_start(str(self.__gateway))
        self.__radio_station.call_handler.deregister_for_incoming_dtmf(str(self.__gateway))
        self.__recording_stop_time = datetime.now()

        #Ask what to do with the recording
        ctr = 0
        is_finalized = False
        while ctr < 3 and not is_finalized:
            self.__post_recording_option = self.__play_and_get_specific_dtmf(call_uuid, os.path.join(DefaultConfig.CONTENT_DIR, self.__menu.finalization_prompt), ["1","2","3"], 15, 3)
            if self.__post_recording_option == None:
                self.__finalize()
            elif self.__post_recording_option == "1": #Listen to the recording
                self.__play(call_uuid, audio_path)
            elif self.__post_recording_option == "2": #save the reording
                self.__save_message(filename, self.__call['Caller-ANI'], datetime.now(), (self.__recording_stop_time - self.__recording_start_time).seconds, int(self.__category_id), datetime.now() + timedelta(int(self.__num_days), 0), self.__radio_station.station)
                is_finalized = True
            elif self.__post_recording_option == "3": #Discard
                is_finalized = True  #Just do not save the recording to the DB
            ctr = ctr +1

        #play that last thank you, goodbye message
        self.__play(call_uuid, os.path.join(DefaultConfig.CONTENT_DIR, self.__menu.goodbye_message))
        
        #clean up, hangup
        self.__finalize()
