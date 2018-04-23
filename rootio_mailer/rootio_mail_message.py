import logging
import smtplib
from rootio.config import *

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class RootIOMailMessage:

    def __init__(self):
        self.__message = ''
        self.__initialize_message()
        #print "mail server is {0}".format(MAIL_USERNAME)


    def __initialize_message(self):
        self.__to = []
        self.__from = ''
        self.__subject = ''
        self.__body = ''

    def add_to_address(self, to_address):
        self.__to.append(to_address)
    
    def set_from(self, from_address):
        self.__from = from_address

    def set_subject(self, subject):
        self.__subject = "SUBJECT: %s " % (subject)

    def set_body(self, body):
        self.__body = body

    def append_to_body(self, extra_body):
        self.__body = "\n".join((self.__body, extra_body))

    def send_message(self):
        log.info("Send message")
        log.info("from: %r", self.__from)
        log.info("to: %r", self.__to)
        log.info("subject: %r", self.__subject)
        log.info("body: %r", self.__body)
