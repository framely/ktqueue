import tornado.web
import tornado.websocket

import logging

from .utils import convert_asyncio_task

client = set()

class MonitorPubWSHandler(tornado.websocket.WebSocketHandler):

    @convert_asyncio_task
    async def open(self, hostname):
        self.hostname = hostname 
        logging.info("Hostname:%s Add Pub." %hostname)

    def on_close(self):
        logging.info("Hostname:%s Add Close." %self.hostname)

    def on_message(self, message):
        for c in client:
            c.write_message(message)

class MonitorSubWSHandler(tornado.websocket.WebSocketHandler):
    @convert_asyncio_task
    async def open(self, hostname):
        client.add(self)

    def on_close(self):
        client.remove(self)

    def on_message(self, message):
        pass