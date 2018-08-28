# encoding: utf-8
import json

from .utils import BaseHandler
from .utils import convert_asyncio_task


class ImageHandler(BaseHandler):
    def initialize(self, mongo_client):
        self.mongo_client = mongo_client
        self.image_collection = mongo_client.ktqueue.images

    @convert_asyncio_task
    async def get(self):
        image_result = self.image_collection.find()
        images = []
        image_prefix = 'in.fds.so:5000/'
        for x in image_result:
            for tag_name in x['tags']:
                image_name = image_prefix + x['name'] + ':' + tag_name
                images.append(image_name)
        if image_result:
            self.write(json.dumps({'images': images}))
        else:
            self.write(json.dumps([]))
