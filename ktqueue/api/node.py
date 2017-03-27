# encoding: utf-8
from collections import defaultdict

import tornado.web

from .utils import convert_asyncio_task

node_used_gpus = defaultdict(lambda: dict())


class NodesHandler(tornado.web.RequestHandler):

    def initialize(self, k8s_client, mongo_client):
        self.k8s_client = k8s_client
        self.mongo_client = mongo_client

    @convert_asyncio_task
    async def get(self):
        def used_gpus(node):
            result = 0
            for job, num in node_used_gpus[node].items():
                result += num
            return result

        ret = await self.k8s_client.call_api(
            api='/api/v1/nodes',
            method='GET',
        )

        self.write({'items': [{
            'name': node['metadata']['name'],
            'labels': node['metadata']['labels'],
            'gpu_used': used_gpus(node['metadata']['name']),
            'jobs': node_used_gpus[node['metadata']['name']],
            'gpu_capacity': node['status']['capacity']['alpha.kubernetes.io/nvidia-gpu'],
        } for node in ret['items']
        ]})
