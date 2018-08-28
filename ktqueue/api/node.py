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

        gpu_usages = await self.k8s_client.call_api(
            api='/api/v1/namespaces/ktqueue/pods',
            method='GET',
        )
        gpu_dict = {}
        for gpu_usage in gpu_usages['items']:
            spec = gpu_usage.get('spec', {})
            if spec:
                gpu = sum(
                    [
                        int(c.get('resources', {}).get('limits', {}).get('nvidia.com/gpu', '0'))
                        for c in spec.get('containers', [])
                    ]
                )
                node_name = spec.get('nodeName', '')
                status = gpu_usage.get('status', {}).get('phase', '')
                if status and node_name and gpu and status == 'Running':
                    gpu_dict[node_name] = gpu_dict.get(node_name, 0) + gpu
            else:
                continue

        ret = await self.k8s_client.call_api(
            api='/api/v1/nodes',
            method='GET',
        )

        self.write({'items': [{
            'name': node['metadata']['name'],
            'labels': node['metadata']['labels'],
            'gpu_used': gpu_dict.get(node['metadata']['name'], 0),
            'jobs': node_used_gpus[node['metadata']['name']],
            'gpu_capacity': node['status']['capacity'].get('nvidia.com/gpu', 0),
        } for node in ret['items']
        ]})
