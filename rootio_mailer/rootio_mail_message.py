import smtplib
from rootio.config import DefaultConfig


class RootIOMailMessage:

    def __init__(self):
        self.__smtp_server = DefaultConfig.MAIL_SERVER
        self.__smtp_username = DefaultConfig.MAIL_USERNAME
        self.__smtp_password = DefaultConfig.MAIL_PASSWORD
        self.__message = ''
        self.__to = []
        self.__from = ''
        self.__subject = ''
        self.__body = ''

    def add_to_address(self, to_address):
        self.__to.append(to_address)

    def set_from(self, from_address):
        self.__from = from_address

    def set_subject(self, subject):
        self.__subject = "SUBJECT: %s " % subject

    def set_body(self, body):
        self.__body = body

    def append_to_body(self, extra_body):
        self.__body = "\n".join((self.__body, extra_body))

    def send_message(self):
        try:
            smtp_server = smtplib.SMTP(self.__smtp_server)
            smtp_server.starttls()
            smtp_server.login(self.__smtp_username, self.__smtp_password)
            smtp_server.sendmail(self.__from, self.__to, "\n\n".join((self.__subject, self.__body)))
            smtp_server.quit()
            return True
        except Exception as e:
            raise e
