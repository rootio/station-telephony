# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="HP Envy"
__date__ ="$Nov 19, 2014 2:15:22 PM$"

from freeswitchESL.ESL import *
from rootio.config import *
from rootio.telephony import *
from rootio.telephony.models import Gateway, Call
import threading
import json
import time
from sets import Set
from datetime import datetime

class CallHandler:
    
    def __init__(self, radio_station, config={}):
        self.__radio_station = radio_station
        self.config = config
        self.__incoming_call_recipients = dict()
        self.__incoming_dtmf_recipients = dict()
        self.__outgoing_call_recipients = dict()
        self.__host_call_recipients = dict()
        self.__waiting_call_recipients = dict()
        self.__call_hangup_recipients = dict()
        self.__available_calls = dict()
        self.__media_playback_stop_recipients = dict()
        
        #get the gateways to be used for telephony
        self.__radio_station.logger.info("Done with Call handler Init")
        self.__load_incoming_gateways()
        self.__load_outgoing_gateways()
        
        #start listener for ESL events
        self.__start_ESL_listener()
    
    def __start_ESL_listener(self):
        t = threading.Thread(target=self.__listen_for_ESL_events, args=())
        t.daemon = True
        t.start()

    def create_esl(self):
        ESL_SERVER = self.config.get('ESL_SERVER', '127.0.0.1')
        ESL_PORT = self.config.get('ESL_PORT', 8021)
        ESL_AUTHENTICATION = self.config.get('ESL_AUTHENTICATION', 'ClueCon')
        return ESLconnection(ESL_SERVER, ESL_PORT,  ESL_AUTHENTICATION)

    def __load_incoming_gateways(self):
        gws = self.__radio_station.db.query(Gateway).join(Gateway.stations_using_for_incoming).filter_by(id=self.__radio_station.id).all()
        self.__incoming_gateways = dict()
        self.__available_incoming_gateways = []
        for gw in gws:
            print gw.number_bottom
            self.__incoming_gateways[str(gw.number_bottom)] = gw
            self.__available_incoming_gateways.append(gw.number_bottom)
            self.__available_incoming_gateways.sort()
            self.__radio_station.logger.info("Got incoming gateways for {0} {1}".format(self.__radio_station.station.name, str(self.__available_incoming_gateways)))
    
    def __load_outgoing_gateways(self):
        gws = self.__radio_station.db.query(Gateway).join(Gateway.stations_using_for_outgoing).filter_by(id=self.__radio_station.id).all()
        self.__outgoing_gateways = dict()
        self.__available_outgoing_gateways = []
        for gw in gws:
            print gw.number_bottom
            self.__outgoing_gateways[str(gw.number_bottom)] = gw
            self.__available_outgoing_gateways.append(gw.number_bottom)
            self.__available_outgoing_gateways.sort()
            self.__radio_station.logger.info("Got outgoing gateways for {0} {1}".format(self.__radio_station.station.name, str(self.__available_outgoing_gateways)))
    
    def __do_ESL_command(self, ESL_command):
        self.__radio_station.logger.info("Executing ESL Command: {0}".format(ESL_command))
        con = self.create_esl()
        result = con.api(ESL_command)
        try:
            con.disconnect()
            return result.getBody()
        except Exception, e:
            self.__radio_station.logger.error(str(e))
            return None

    def register_for_call_hangup(self, recipient, to_number):
        self.__call_hangup_recipients[to_number] = recipient
        self.__radio_station.logger.info("Added {0} to incoming call hangup recipients {1}".format(recipient, str(self.__call_hangup_recipients)))

    def register_for_host_call(self, recipient, host_number):
        self.__host_call_recipients[host_number] = recipient
        self.__radio_station.logger.info("The program {0} is now listening for host calls from {1}".format(recipient, host_number))

    def register_for_incoming_calls(self, recipient):
        for incoming_gateway in self.__incoming_gateways:
            self.__incoming_call_recipients[incoming_gateway] = recipient
            self.__radio_station.logger.info("Added {0} to incoming call recipients {1}".format(recipient, str(self.__incoming_call_recipients)))

    def register_for_incoming_dtmf(self, recipient, from_number):
        self.__incoming_dtmf_recipients[from_number] = recipient
        self.__radio_station.logger.info("Added {0} to incoming dtmf recipients {1}".format(recipient, str(self.__incoming_dtmf_recipients)))
        
    def deregister_for_incoming_dtmf(self, from_number):
        del self.__incoming_dtmf_recipients[from_number]
    
    def register_for_media_playback_stop(self, recipient, from_number):
        self.__media_playback_stop_recipients[from_number] = recipient
        self.__radio_station.logger.info("Added {0} to media playback stop recipients {1}".format(recipient, str(self.__media_playback_stop_recipients)))

    def deregister_for_incoming_calls(self, recipient):
        self.__incoming_call_recipients = dict()
        self.__radio_station.logger.info("Removed {0} from call hangup recipients {1}".format(recipient, str(self.__incoming_call_recipients)))

    def deregister_for_call_hangup(self, recipient, from_number):
        if from_number in self.__call_hangup_recipients:
            del self.__call_hangup_recipients[from_number]
            self.__radio_station.logger.info("Removed {0} from call hangup recipients {1}".format(recipient, str(self.__call_hangup_recipients)))

    def deregister_for_media_playback_stop(self, recipient, from_number):
        if from_number in self.__media_playback_stop_recipients:
            del self.__media_playback_stop_recipients[from_number]
            self.__radio_station.logger.info("Removed {0} from media playback stop recipients {1}".format(recipient, str(self.__media_playback_stop_recipients)))

    def call(self, program_action, to_number, action, argument, time_limit):
        if to_number in self.__available_calls.keys():
            self.__radio_station.logger.info("Existing call to {0} requested for action on argument '{1}, being returned".format(to_number, argument))
            program_action.notify_call_answered(self.__available_calls[to_number])
            return True
        else:
            self.__radio_station.logger.info("GWS before pop are {0}".format(str(self.__available_outgoing_gateways)))
            gw = self.__outgoing_gateways[str(self.__available_outgoing_gateways.pop())[-9:]]
            self.__radio_station.logger.info("GWS after pop are {0}".format(str(self.__available_outgoing_gateways)))
            call_command = 'originate {{{0}}}{1}/{2}{3} &conference("{4}_{5}")'.format(gw.extra_string, gw.sofia_string, gw.gateway_prefix, to_number, program_action.program.id, program_action.program.radio_station.id)
            self.__radio_station.logger.info("setting up new call for argument '{0}': {1}".format(argument, call_command))
            self.__waiting_call_recipients[to_number] = program_action
            result = self.__do_ESL_command(call_command)
            self.__radio_station.logger.info("Result of call ESL command is {0}".format(result))
            if result == None or result.split(" ")[0] != "+OK":
                self.__available_outgoing_gateways.append(gw.number_bottom)
                self.__available_outgoing_gateways.sort()
            self.__radio_station.logger.info("GWS after call are {0}".format(str(self.__available_outgoing_gateways)))
            return result != None and result.split(" ")[0] == "+OK"

    def bridge_incoming_call(self, call_UUID, program_action):
        bridge_command = 'uuid_transfer {0} conference:"{1}"@default inline'.format(call_UUID, '{0}_{1}'.format(program_action.program.id, program_action.program.radio_station.id))
        self.__radio_station.logger.info("Bridging call from {0} into conference {1}".format(call_UUID, '{0}_{1}'.format(program_action.program.id, program_action.program.radio_station.id)))
        return self.__do_ESL_command(bridge_command)

    def schedule_hangup(self, seconds, call_UUID):
        hangup_command = 'sched_hangup +{} {}'.format(seconds, call_UUID)
        self.__radio_station.logger.info("setting up hangup for {0} seconds into call with UUID {1}".format(seconds, call_UUID))
        return self.__do_ESL_command(hangup_command)
        
    def hangup(self, call_UUID):
        self.__radio_station.logger.info("preparing hangup for call with UUID {0}".format(call_UUID))
        hangup_command = 'uuid_kill {}'.format(call_UUID)
        self.__radio_station.logger.info("ordering hangup for call with UUID {0}".format(call_UUID))
        self.__do_ESL_command(hangup_command) #possibly segfaults
           
    
    def play(self, call_UUID, file_location):
        play_command = 'uuid_displace {0} start \'{1}\''.format(call_UUID, file_location.replace("'", r"\'")) 
        self.__radio_station.logger.info("Playing file {0} into call with UUID {1}".format(file_location, call_UUID))
        return self.__do_ESL_command(play_command)
    
    def stop_play(self, call_UUID, content_location):
        stop_play_command = 'uuid_displace {0} stop \'{1}\''.format(call_UUID, content_location.replace("'", r"\'"))
        return self.__do_ESL_command(stop_play_command)

    def speak(self, phrase, call_UUID):
        speak_command = 'speak stuff'
        return self.__do_ESL_command(speak_command) 
        
    def __listen_for_ESL_events(self):
        ESLConnection = self.create_esl()
        ESLConnection.events("plain", "all")
        while 1:
            e = ESLConnection.recvEvent()
            if e:
                event_json_string = e.serialize('json')
                event_json = json.loads(event_json_string)
                event_name = e.getHeader("Event-Name")
                if event_name == "CHANNEL_ANSWER":
                    #self.__available_calls[str(event_json['Caller-Destination-Number'])[-10:]] = event_json
                    self.__radio_station.logger.info("received answer for {0} with waiting recipients {1}".format(event_json['Caller-Destination-Number'], self.__waiting_call_recipients.keys()))
                    #self.__record_call(event_json['Channel-Call-UUID'], event_json['variable_sip_from_user'], event_json['Caller-Destination-Number'])
                    if str(event_json['Caller-Destination-Number'])[-10:] in self.__waiting_call_recipients:
                        self.__available_calls[str(event_json['Caller-Destination-Number'])[-10:]] = event_json
                        self.__record_call(event_json['Channel-Call-UUID'], event_json['variable_sip_from_user'], event_json['Caller-Destination-Number'])
                        self.__waiting_call_recipients[str(event_json['Caller-Destination-Number'])[-10:]].notify_call_answered(event_json)
                        self.__radio_station.logger.info("Deleting recipient {0} from waiting call recipients {1}".format(str(event_json['Caller-Destination-Number'])[-10:], self.__waiting_call_recipients))
                        del self.__waiting_call_recipients[str(event_json['Caller-Destination-Number'])[-10:]]
               
                elif event_name == "DTMF":
                    if 'Caller-Destination-Number' in event_json and str(event_json['Caller-Destination-Number'])[-10:] in self.__incoming_dtmf_recipients:
                        self.__radio_station.logger.info("Received DTMF [{0}] for recipient {1} in {2}".format(event_json["DTMF-Digit"], event_json['Caller-Destination-Number'], self.__incoming_dtmf_recipients))
                        self.__incoming_dtmf_recipients[str(event_json['Caller-Destination-Number'])[-10:]].notify_incoming_dtmf(event_json)
    
                elif event_name == "CHANNEL_HANGUP":
                    loggable = False
                    if 'Caller-Destination-Number' in event_json:
                        if str(event_json['Caller-Destination-Number'])[-10:] in self.__call_hangup_recipients:
                            self.__call_hangup_recipients[str(event_json['Caller-Destination-Number'])[-10:]].notify_call_hangup(event_json)
                            loggable = True
                        #remove the call from the list of available calls
                        if str(event_json['Caller-Destination-Number'])[-10:] in self.__available_calls:
                            self.__radio_station.logger.info("Removing call to {0} from available calls {1}".format(str(event_json['Caller-Destination-Number'])[-10:],  self.__available_calls.keys()))
                            del self.__available_calls[str(event_json['Caller-Destination-Number'])[-10:]]
                            self.__release_gateway(event_json)
                            loggable = True
                        #log the call
                        if loggable:
                            self.__log_call(event_json)            
       
                    if event_json['Caller-Destination-Number'] in self.__media_playback_stop_recipients:
                        del self.__media_playback_stop_recipients[event_json['Caller-Destination-Number']]
              
                elif event_name == "CHANNEL_PARK":
                    self.__radio_station.logger.info("Notifying recipient for {0} in {1} and {2}".format(event_json['Caller-Destination-Number'][-9:], self.__incoming_call_recipients, self.__host_call_recipients))
                    if 'Caller-Destination-Number' in event_json:
                        if event_json['Caller-Destination-Number'][-9:] in self.__incoming_call_recipients: #Someone calling into a talk show
                            self.__incoming_call_recipients[event_json['Caller-Destination-Number'][-9:]].notify_incoming_call(event_json)
                        elif event_json['Caller-ANI'][-9:] in self.__host_call_recipients:
                            self.__host_call_recipients[event_json['Caller-ANI'][-9:]].notify_host_call(event_json)
                            
    
              
                elif event_name == "MEDIA_BUG_STOP":
                    try:
                        if 'Caller-Destination-Number' in event_json and event_json['Caller-Destination-Number'] in  self.__media_playback_stop_recipients:
                            #self.__radio_station.logger.info("got media stop bug as {0}".format(event_json_string))
                            self.__radio_station.logger.info("Notifying media playback stop recipient for {0} in {1}".format(event_json['Caller-Destination-Number'], self.__media_playback_stop_recipients))
                            self.__media_playback_stop_recipients[event_json['Caller-Destination-Number']].notify_media_play_stop(event_json)
                            #del self.__media_playback_stop_recipients[event_json['Caller-Destination-Number']]
                    except e:
                        print str(e) 

    def __record_call(self, call_UUID, from_number, destination_number):
        record_command = "uuid_record {0} start '/home/amour/test_media/RootioNew/Northern Uganda Pilot/Luo_Recordings/Call_Recordings/{1}_{2}_{3}_recording.wav'".format(call_UUID, from_number, destination_number, time.strftime("%Y_%m_%d_%H_%M_%S"))
        self.__radio_station.logger.info("setting up recording for call with UUID {0}".format(call_UUID))
        result = self.__do_ESL_command(record_command)

    def __log_call(self, event_json):
        call = Call()
        call.call_uuid = event_json['Channel-Call-UUID']
        call.start_time = datetime.fromtimestamp(float(event_json['Caller-Channel-Answered-Time'][0:-6]))
        call.duration = (datetime.fromtimestamp(float(event_json['Event-Date-Timestamp'][0:-6])) - call.start_time).seconds
        call.from_phonenumber = event_json['Caller-ANI']
        call.to_phonenumber = event_json['Caller-Destination-Number']
        call.station_id = self.__radio_station.station.id
        self.__radio_station.db._model_changes = {}
        self.__radio_station.db.add(call)
        self.__radio_station.db.commit()

    def __release_gateway(self, event_json):
        #if it was an incoming call
        print "attempting to release {0} from gateways {1}".format(event_json['Caller-ANI'][-9:], self.__outgoing_gateways.keys())
        if 'Caller-Destination-Number' in event_json and event_json['Caller-Destination-Number'][:-9] in self.__outgoing_gateways.keys():
            self.__radio_station.logger.info("Putting back gateway {0} to available gateways {1}".format(event_json['Caller-Destination-Number'][:-9], self.__outgoing_gateways))
            self.__available_outgoing_gateways.append(event_json['Caller-Destination-Number'])
        #if it is an outbound call
        if 'Caller-ANI' in event_json and event_json['Caller-ANI'][-9:] in self.__outgoing_gateways.keys():
            self.__radio_station.logger.info("Putting back gateway {0} to available gateways {1}".format(event_json['Caller-ANI'][:-9], self.__outgoing_gateways))
            self.__available_outgoing_gateways.append(int(event_json['Caller-ANI'][-9:]))
        self.__available_outgoing_gateways.sort()
