# encoding: utf-8
import json
from .utils import BaseHandler
from .utils import convert_asyncio_task

class TagHandler(BaseHandler):
    def initialize(self, mongo_client):
        self.mongo_client = mongo_client
        self.tags_collection = mongo_client.ktqueue.setting

    @convert_asyncio_task
    async def get(self):
        mgResult = self.tags_collection.find_one({'name': 'tags'})
        if mgResult:
            self.write(json.dumps(mgResult['data']))
        else:
            self.write(json.dumps([]))
