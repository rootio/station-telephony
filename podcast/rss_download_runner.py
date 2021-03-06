# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="HP Envy"
__date__ ="$Nov 19, 2014 4:16:15 PM$"

import sys
sys.path.append('/usr/local/rootio_web/')
from rootio.config import *
from daemon.daemoner import Daemon
from rss_agent import RSSAgent
from datetime import datetime
import threading
import logging
from logging.handlers import TimedRotatingFileHandler 

class RSSRunner(Daemon):

    def run(self):
        app_logger = logging.getLogger('rss_downloader')
        hdlr = TimedRotatingFileHandler('/var/log/rootio/rssdownloader.log',when='midnight',interval=1)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        app_logger.addHandler(hdlr)
        app_logger.setLevel(logging.DEBUG)

        rss_server = RSSAgent(app_logger)
        rss_server.run()
        print "================ RSS runner service started at {0} ==============".format(datetime.utcnow())



if __name__ == "__main__":
    rss_daemon = RSSRunner("/tmp/rss_runner.pid")
    if(len(sys.argv) == 2):
        if sys.argv[1] == "start":
            rss_daemon.start()
        elif sys.argv[1] == "stop":
           rss_daemon.stop()
        elif sys.argv[1] == "restart": 
            rss_daemon.restart()
        else:
            print "Wrong arguments supplied. Usage: rss_download_runner start|stop|restart"
    else:
        print "Wrong number of arguments supplied. Usage: rss_download_runner start|stop|restart"
