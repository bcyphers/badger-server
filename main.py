import sys
import json
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from sqlalchemy import create_engine, Table, Column, Integer, String, Text, DateTime, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


# create sqlalchemy engine
engine = create_engine('mysql://root@localhost/badgersett')
Base = declarative_base(engine)
get_session = sessionmaker(bind=engine)


# table for logging all third party requests and the actions privacy badger
# would have taken on them
class Request(Base):
    __tablename__ = 'requests'

    id = Column(Integer, primary_key=True)
    time = Column(DateTime)
    req_url = Column(String(2000))
    req_host = Column(String(255))
    req_origin = Column(String(255))
    page_url = Column(String(2000))
    page_host = Column(String(255))
    page_origin = Column(String(255))
    action = Column(String(50))

    def __init__(self, time, req_url, req_host, req_origin, page_url, page_host,
                 page_origin, action):
        dt = datetime.datetime.fromtimestamp(time/1000)
        self.time = dt.isoformat(sep=' ', timespec='milliseconds')
        self.req_url = req_url
        self.req_host = req_host
        self.req_origin = req_origin
        self.page_url = page_url
        self.page_host = page_host
        self.page_origin = page_origin
        self.action = action

    def __repr__(self):
        return "<Request('%s', '%s', '%s')>" % (
            self.page_host, self.req_url, self.action)


# table for all tracking actions
class Tracker(Base):
    __tablename__ = 'tracking_actions'

    id = Column(Integer, primary_key=True)
    time = Column(DateTime)
    tracker_url = Column(String(2000))
    tracker_host = Column(String(255))
    tracker_origin = Column(String(255))
    page_url = Column(String(2000))
    page_host = Column(String(255))
    page_origin = Column(String(255))
    type = Column(String(25))
    details = Column(Text)

    def __init__(self, time, tracker_url, tracker_host, tracker_origin,
                 page_url, page_host, page_origin, type, details):
        dt = datetime.datetime.fromtimestamp(time/1000)
        self.time = dt.isoformat(sep=' ', timespec='milliseconds')
        self.tracker_url = tracker_url
        self.tracker_host = tracker_host
        self.tracker_origin = tracker_origin
        self.page_url = page_url
        self.page_host = page_host
        self.page_origin = page_origin
        self.type = type
        self.details = details

    def __repr__(self):
        return "<Tracker('%s', '%s', '%s')>" % (
            self.page_host, self.tracker_url, self.type)


# create or connect to tables and map them to ORM classes
def setup():
    metadata = MetaData(engine)
    metadata.create_all(engine)


# class for handling POST requests from the instrumented Privacy Badger
class BadgerRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        raw = self.rfile.read(content_length).decode('utf-8')
        js = json.loads(raw)

        # connect to database and get sqlalchemy session
        session = get_session()

        # parse out request data
        table = js['table']
        data = js['data']

        # create new request entry
        if table == 'requests':
            row = Request(
                time=data['time'],
                req_url=data['req_url'],
                req_host=data['req_host'],
                req_origin=data['req_origin'],
                page_url=data['page_url'],
                page_host=data['page_host'],
                page_origin=data['page_origin'],
                action=data['action'])

        # create new tracking action entry
        elif table == 'tracking_actions':
            row = Tracker(
                time=data['time'],
                tracker_url=data['tracker']['tracker_url'],
                tracker_host=data['tracker_host'],
                tracker_origin=data['tracker_origin'],
                page_url=data['tracker']['page_url'],
                page_host=data['tracker']['page_host'],
                page_origin=data['page_origin'],
                type=data['tracker']['type'],
                details=data['tracker']['details'])

        # enter into database
        try:
            session.add(row)
            session.commit()
        except:
            session.rollback()
        finally:
            session.close()

        # send an empty 200 response
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()


# run the webserver
def run(port=8080):
    httpd = HTTPServer(('', port), BadgerRequestHandler)
    print('starting httpd...')
    httpd.serve_forever()


if __name__ == '__main__':
    setup()

    if len(sys.argv) > 1:
        run(port=int(sys.argv[1]))
    else:
        run()
