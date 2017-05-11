from memory_profiler import profile
from rss_downloader import RSSDownloader
import os
from time import sleep
import feedparser
from datetime import datetime, timedelta
from time import mktime
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from rootio.content.models import ContentPodcast, ContentPodcastDownload
from rootio.config import DefaultConfig
import threading 
from Queue import Queue

class RSSAgent:
    def __init__(self, logger):
        self.logger = logger
        self.q = Queue()

    def __get_podcast_tracks(self):
        engine = create_engine(DefaultConfig.SQLALCHEMY_DATABASE_URI)
        session = sessionmaker(bind=engine)()
        return session.query(ContentPodcast).all()

    def run(self):
        print("running....")
        while True:
            print "found podcasts " + str(len(self.__get_podcast_tracks()))
            for podcast_track in self.__get_podcast_tracks():
                pd = RSSDownloader(podcast_track.id)
                thr = threading.Thread(target=pd.download)
                thr.daemon = True
                thr.start()
            sleep(300) #5 minutes

    @profile
    def download_serial(self):
        print "downloading serial:" + str(len(self.__get_podcast_tracks()))
        for podcast_track in self.__get_podcast_tracks():
            pd = RSSDownloader(podcast_track.id)
            pd.download()

    @profile
    def download_parallel(self):
        threads = []
        print "found podcasts " + str(len(self.__get_podcast_tracks()))
        for podcast_track in self.__get_podcast_tracks():
            pd = RSSDownloader(podcast_track.id)
            thr = threading.Thread(target=pd.download)
            thr.daemon = True
            threads.append(thr)

        for thrd in threads:
            thrd.start()

        for thrd in threads:
            thrd.join()

    def worker(self):
        while not self.q.empty():
            print "starting download..."
            pd = self.q.get()
            pd.download()
            print "finished download"
            
        

    @profile
    def download_pooled(self, num_workers):
        print "downloading with {0} workers".format(num_workers,)
        for podcast_track in self.__get_podcast_tracks():
            self.q.put(RSSDownloader(podcast_track.id))
        threads = []

        for i in range(num_workers):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()
        #self.q.join()
