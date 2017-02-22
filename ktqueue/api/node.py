# encoding: utf-8
import tornado.web

from .utils import convert_asyncio_task


class NodesHandler(tornado.web.RequestHandler):

    def initialize(self, k8s_client, mongo_client):
        self.k8s_client = k8s_client
        self.mongo_client = mongo_client

    @convert_asyncio_task
    async def get(self):
        ret = await self.k8s_client.call_api(
            api='/api/v1/nodes',
            method='GET',
        )

        self.write({'items': [{
            'name': node['metadata']['name'],
            'labels': node['metadata']['labels']
        } for node in ret['items']
        ]})
