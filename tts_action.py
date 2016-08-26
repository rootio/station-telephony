# -*- coding: utf-8 -*-
from rootio.config import *
import plivohelper
import json


class TTSAction:
    def __init__(self, argument, start_time, duration, is_streamed, program, hangup_on_complete=False):
        self.__argument = argument
        self.__call_answer_info = ''
        self.__is_valid = True
        self.start_time = start_time
        self.duration = duration
        self.__is_streamed = is_streamed
        self.program = program
        self.__hangup_on_complete = hangup_on_complete
        self.__call_handler = self.program.radio_station.call_handler
        self.program.radio_station.logger.info("Done initing TTS action for program {0}".format(self.program.name))
        self.program.log_program_activity("Done initing TTS action for program {0}".format(self.program.name))

    def start(self):
        if self.__is_valid:
            self.program.set_running_action(self)
            call_result = self.__request_call()
            if call_result != True:  # !!
                print "call_result is not true!!"
                self.stop()

    def stop(self):
        self.program.radio_station.logger.info('stop tts')
        self.__stop_speak()
        self.program.notify_program_action_stopped(self)

    def notify_call_answered(self, answer_info):
        self.program.radio_station.logger.info("Received call answer notification for TTS action of {0} program".format(self.program.name))
        self.program.log_program_activity("Received call answer notification for TTS action of {0} program".format(self.program.name))
        self.__call_answer_info = answer_info
        self.__speak_stuff(self.__call_answer_info['Channel-Call-UUID'], self.__argument)
        self.__listen_for_speak_stop()

    def __load_media(self):  # load the media to be played
        pass

    def __request_call(self):
        self.program.radio_station.logger.info('ask for call')
        return self.__call_handler.call(self, self.program.radio_station.station.transmitter_phone.number, 'speak',
                                        'speak', self.duration)

    def __speak_stuff(self, call_UUID, message):  # play the media in the array
        self.program.radio_station.logger.info('will speak')
        try:
            message = message.replace("(", ",")
            message = message.replace(")", ",")  # removes the bug that makes FS send a bye signal do TTS server.
            message = message.replace("\n", " ")  # Remove the new line character people can envetually send and makes FS stop the TTS
            self.program.radio_station.logger.info(message)
            message = message.encode('utf8')
            result = self.__call_handler.speak(message, call_UUID)
            self.program.log_program_activity('result of speak is ' + result)
        except Exception, e:
            self.program.radio_station.logger.error(str(e))
            return

    def __stop_speak(self):  # stop the media being played by the player
        try:
            result = self.__call_handler.break_speak(self.__call_answer_info['Channel-Call-UUID'])
            self.program.log_program_activity('result of stop speak is ' + result)
        except Exception, e:
            self.program.radio_station.logger.error(str(e))
            return

    def notify_speak_stop(self, speak_stop_info):
        self.program.radio_station.logger.info(
            "Speaked all text, stopping speaking in TTS action for {0}".format(self.program.name))
        self.__call_handler.deregister_for_speak_stop(self,self.__call_answer_info['Caller-Destination-Number'])
        if self.__hangup_on_complete:
            self.program.radio_station.logger.info("Hangup on complete is true for {0}".format(self.program.name))
            self.program.log_program_activity("Hangup on complete is true for {0}".format(self.program.name))
            self.program.radio_station.logger.info(
                "Deregistered, all good, about to order hangup for {0}".format(self.program.name))
            self.program.log_program_activity(
                "Deregistered, all good, about to order hangup for {0}".format(self.program.name))
            self.__call_handler.hangup(self.__call_answer_info['Channel-Call-UUID'])
            self.program.notify_program_action_stopped(self)

        self.__is_valid = False

    def __listen_for_speak_stop(self):
        self.__call_handler.register_for_speak_stop(self, self.__call_answer_info['Caller-Destination-Number'])