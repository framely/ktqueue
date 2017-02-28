# encoding: utf-8
import json
import os
import logging

import tornado.web

from ktqueue.cloner import Cloner
from .utils import convert_asyncio_task
from ktqueue.utils import save_job_log
from ktqueue import settings


class JobsHandler(tornado.web.RequestHandler):

    def initialize(self, k8s_client, mongo_client):
        self.k8s_client = k8s_client
        self.mongo_client = mongo_client
        self.jobs_collection = mongo_client.ktqueue.jobs

    @convert_asyncio_task
    async def post(self):
        """
        Create a new job.
        e.x. request:
            {
                "name": "test-17",
                "command": "echo 'aW1wb3J0IHRlbnNvcmZsb3cgYXMgdGYKaW1wb3J0IHRpbWUKc2Vzc2lvbiA9IHRmLlNlc3Npb24oKQpmb3IgaSBpbiByYW5nZSg2MDApOgogICAgdGltZS5zbGVlcCgxKQogICAgcHJpbnQoaSkK' | base64 -d | python3",
                "gpu_num": 1,
                "image": "comzyh/tf_image",
                "repo": "https://github.com/comzyh/TF_Docker_Images.git",
                "commit_id": "3701b94219fb06974f485cabf99ad88019afe618"
            }
        """
        body_arguments = json.loads(self.request.body.decode('utf-8'))

        name = body_arguments.get('name')

        # job with same name is forbidden
        if self.jobs_collection.find_one({'name': name}):
            self.set_status(400)
            self.finish(json.dumps({'message': 'Job {} already exists'.format(name)}))
            return

        command = body_arguments.get('command')
        node = body_arguments.get('node', None)
        gpu_num = int(body_arguments.get('gpu_num'))
        image = body_arguments.get('image')
        repo = body_arguments.get('repo', None)
        commit_id = body_arguments.get('commit_id', None)

        command_kube = 'cd $WORK_DIR && ' + command

        job_dir = os.path.join('/cephfs/ktqueue/jobs/', name)
        if not os.path.exists(job_dir):
            os.makedirs(job_dir)

        output_dir = os.path.join('/cephfs/ktqueue/output', name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        volumeMounts = []
        volumes = []
        node_selector = {}

        # add custom volumeMounts
        for volume in body_arguments.get('volumeMounts', []):
            volume_name = 'volume-{}'.format(volume['key'])
            volumes.append({
                'name': volume_name,
                'hostPath': {'path': volume['hostPath']}
            })
            volumeMounts.append({
                'name': volume_name,
                'mountPath': volume['mountPath']
            })

        if node:
            node_selector['kubernetes.io/hostname'] = node

        if gpu_num > 0:
            # cause kubernetes does not support NVML, use this trick to suit nvidia driver version
            command_kube = 'version=$(ls /nvidia-drivers | tail -1); ln -s /nvidia-drivers/$version /usr/local/nvidia &&' + command_kube
            volumes.append({
                'name': 'nvidia-drivers',
                'hostPath': {
                    'path': '/var/lib/nvidia-docker/volumes/nvidia_driver'
                }
            })
            volumeMounts.append({
                'name': 'nvidia-drivers',
                'mountPath': '/nvidia-drivers',
            })

        # cephfs
        volumes.append({
            'name': 'cephfs',
            'hostPath': {
                'path': '/mnt/cephfs'
            }
        })
        volumeMounts.append({
            'name': 'cephfs',
            'mountPath': '/cephfs',
        })

        job = {
            'apiVersion': 'batch/v1',
            'kind': 'Job',
            'metadata': {
                'name': name,
            },
            'spec': {
                'parallelism': 1,
                'template': {
                    'metadata': {
                        'name': name,
                    },
                    'spec': {
                        'containers': [
                            {
                                'name': name + 'container',
                                'image': image,
                                'imagePullPolicy': 'IfNotPresent',
                                'command': ['sh', '-c', command_kube],
                                'resources': {
                                    'limits': {
                                        'alpha.kubernetes.io/nvidia-gpu': gpu_num,
                                    },
                                },
                                'volumeMounts': volumeMounts,
                                'env': [
                                    {
                                        'name': 'JOB_NAME',
                                        'value': name
                                    },
                                    {
                                        'name': 'OUTPUT_DIR',
                                        'value': output_dir
                                    },
                                    {
                                        'name': 'WORK_DIR',
                                        'value': os.path.join(job_dir, 'code')
                                    },
                                    {
                                        'name': 'LC_ALL',
                                        'value': 'en_US.UTF-8'
                                    },
                                    {
                                        'name': 'LC_CTYPE',
                                        'value': 'en_US.UTF-8'
                                    },
                                ]
                            }
                        ],
                        'volumes': volumes,
                        'restartPolicy': 'OnFailure',
                        'nodeSelector': node_selector,
                    }
                }
            }
        }
        self.jobs_collection.update_one({'name': name}, {'$set': {
            'name': name,
            'node': node,
            'command': command,
            'gpu_num': gpu_num,
            'repo': repo,
            'commit_id': commit_id,
            'image': image,
            'status': 'fetching',
            'tensorboard': False,
            'volumeMounts': body_arguments.get('volumeMounts', []),
        }}, upsert=True)
        self.finish(json.dumps({'message': 'job {} successful created.'.format(name)}))
        # clone code
        if repo and commit_id:
            cloner = Cloner(repo=repo, commit_id=commit_id, dst_directory=os.path.join(job_dir, 'code'))
            await cloner.clone_and_copy()

        ret = await self.k8s_client.call_api(
            api='/apis/batch/v1/namespaces/{namespace}/jobs'.format(namespace=settings.job_namespace),
            method='POST',
            data=job
        )
        try:
            self.jobs_collection.update_one({'name': name}, {'$set': {
                'status': 'pending',
                'creationTimestamp': ret['metadata']['creationTimestamp'],
            }}, upsert=True)
        except Exception as e:
            logging.info(ret)
            logging.exception(e)

    async def get(self):
        page = int(self.get_argument('page', 1))
        page_size = int(self.get_argument('page_size', 20))
        count = self.jobs_collection.count()
        jobs = list(self.jobs_collection.find().sort("_id", -1).skip(page_size * (page - 1)).limit(page_size))
        for job in jobs:
            job['_id'] = str(job['_id'])
        self.finish(json.dumps({
            'page': page,
            'total': count,
            'page_size': page_size,
            'data': jobs,
        }))


class JobLogHandler(tornado.web.RequestHandler):

    def initialize(self, k8s_client, mongo_client):
        self.k8s_client = k8s_client
        self.mongo_client = mongo_client
        self.jobs_collection = mongo_client.ktqueue.jobs

    @convert_asyncio_task
    async def get(self, job):
        pods = await self.k8s_client.call_api(
            method='GET',
            api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
            params={'labelSelector': 'job-name={job}'.format(job=job)}
        )
        if len(pods['items']):
            pod_name = pods['items'][0]['metadata']['name']
            resp = await self.k8s_client.call_api_raw(
                method='GET',
                api='/api/v1/namespaces/{namespace}/pods/{pod_name}/log'.format(namespace=settings.job_namespace, pod_name=pod_name)
            )
            if resp.status == 200:
                async for chunk in resp.content.iter_any():
                    self.write(chunk)
                resp.close()
                return
        with open(os.path.join('/cephfs/ktqueue/logs', job, 'log.txt'), 'r') as f:
            self.finish(f.read())


class StopJobHandler(tornado.web.RequestHandler):

    def initialize(self, k8s_client, mongo_client):
        self.k8s_client = k8s_client
        self.mongo_client = mongo_client
        self.jobs_collection = mongo_client.ktqueue.jobs

    @convert_asyncio_task
    async def post(self, job):
        pods = await self.k8s_client.call_api(
            method='GET',
            api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
            params={'labelSelector': 'job-name={job}'.format(job=job)}
        )
        if len(pods['items']):
            pod_name = pods['items'][0]['metadata']['name']
            await save_job_log(job_name=job, pod_name=pod_name, k8s_client=self.k8s_client)
            await self.k8s_client.call_api(
                method='DELETE',
                api='/apis/batch/v1/namespaces/{namespace}/jobs/{name}'.format(namespace=settings.job_namespace, name=job)
            )
            await self.k8s_client.call_api(
                method='DELETE',
                api='/api/v1/namespaces/{namespace}/pods/{name}'.format(namespace=settings.job_namespace, name=pod_name)
            )
        self.jobs_collection.update_one({'name': job}, {'$set': {'status': 'ManualStop'}})
        self.finish({'message': 'Job {} successful deleted.'.format(job)})


class TensorBoardHandler(tornado.web.RequestHandler):

    def initialize(self, k8s_client, mongo_client):
        self.k8s_client = k8s_client
        self.mongo_client = mongo_client
        self.jobs_collection = mongo_client.ktqueue.jobs

    @convert_asyncio_task
    async def post(self, job):
        job_image = self.jobs_collection.find_one({'name': job})['image']
        body_arguments = json.loads(self.request.body.decode('utf-8'))
        logdir = body_arguments.get('logdir', '/cephfs/ktqueue/logs/{job}/train'.format(job=job))
        job_dir = os.path.join('/cephfs/ktqueue/jobs/', job)
        output_dir = os.path.join('/cephfs/ktqueue/output', job)
        command = 'tensorboard --logdir {logdir} --host 0.0.0.0'.format(logdir=logdir)

        pod = {
            'apiVersion': 'v1',
            'kind': 'Pod',
            'metadata': {
                'name': '{job}-tensorboard'.format(job=job),
                'labels': {
                    'ktqueue-tensorboard-job-name': job
                }
            },
            'spec': {
                'containers': [
                    {
                        'name': 'ktqueue-tensorboard',
                        'image': job_image,
                        'command': ['sh', '-c', command],
                        'volumeMounts': [
                            {
                                'name': 'cephfs',
                                'mountPath': '/cephfs',
                            }
                        ],
                        'env': [
                            {
                                'name': 'JOB_NAME',
                                'value': job
                            },
                            {
                                'name': 'OUTPUT_DIR',
                                'value': output_dir
                            },
                            {
                                'name': 'WORK_DIR',
                                'value': os.path.join(job_dir, 'code'),
                            },
                        ]
                    }
                ],
                'volumes': [
                    {
                        'name': 'cephfs',
                        'hostPath': {
                            'path': '/mnt/cephfs'
                        }
                    }
                ]
            }
        }

        ret = await self.k8s_client.call_api(
            api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
            method='POST',
            data=pod
        )
        self.jobs_collection.update_one({'name': job}, {'$set': {'tensorboard': True}})

        self.write(ret)

    @convert_asyncio_task
    async def delete(self, job):
        pods = await self.k8s_client.call_api(
            method='GET',
            api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
            params={'labelSelector': 'ktqueue-tensorboard-job-name={job}'.format(job=job)}
        )
        if len(pods['items']):
            pod_name = pods['items'][0]['metadata']['name']
            ret = await self.k8s_client.call_api(
                api='/api/v1/namespaces/{namespace}/pods/{name}'.format(namespace=settings.job_namespace, name=pod_name),
                method='DELETE',
            )
            self.write(ret)
        else:
            self.set_status(404)
            self.write({'message': 'tensorboard pod not found.'})
        self.jobs_collection.update_one({'name': job}, {'$set': {'tensorboard': False}})
