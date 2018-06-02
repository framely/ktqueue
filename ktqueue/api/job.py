# encoding: utf-8
import json
import os
import re
import logging
import bson
from collections import defaultdict

import tornado.web
import tornado.websocket

from ktqueue.cloner import Cloner
from .utils import convert_asyncio_task
from .utils import BaseHandler
from .utils import apiauthenticated
from ktqueue.utils import k8s_delete_job
from ktqueue.utils import KTQueueDefaultCredentialProvider
from ktqueue import settings


def generate_job(name, command, node, gpu_num, image, repo, branch, commit_id,
                 comments, mounts, load_nvidia_driver=None, cpu_limit=None, memory_limit=None, auto_restart=False):
    """Generate a job description in JSON format."""

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
    for volume in mounts:
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

    if gpu_num > 0 or load_nvidia_driver:
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

    # resources
    resources = {
        'limits': {
            # 'alpha.kubernetes.io/nvidia-gpu': gpu_num,
            'nvidia.com/gpu': gpu_num,
        },
    }

    if cpu_limit:
        resources['limits']['cpu'] = cpu_limit

    if memory_limit:
        resources['limits']['memory'] = memory_limit

    # cephfs
    volumes.append(settings.sfs_volume)
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
                            'name': 'ktqueue-job',
                            'image': image,
                            # 'imagePullPolicy': 'IfNotPresent',
                            'command': ['sh', '-c', command_kube],
                            'resources': resources,
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
                    'restartPolicy': 'OnFailure' if auto_restart else 'Never',
                    'nodeSelector': node_selector,
                }
            }
        }
    }
    return job


async def clone_code(name, repo, branch, commit_id, jobs_collection, job_dir, crediential):
    # clone code
    if repo:
        try:
            cloner = Cloner(repo=repo, dst_directory=os.path.join(job_dir, 'code'),
                            branch=branch, commit_id=commit_id, crediential=crediential)
            await cloner.clone_and_copy()
        except Exception as e:
            jobs_collection.update_one({'name': name}, {'$set': {'status': 'FetchError'}})
            raise
        if not commit_id:
            jobs_collection.update_one({'name': name}, {'$set': {'commit': cloner.commit_id}})
    else:
        os.makedirs(os.path.join('/cephfs/ktqueue/jobs', name, 'code'))


class JobsHandler(BaseHandler):

    __job_name_pattern = re.compile(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$')

    def initialize(self, k8s_client, mongo_client):
        self.k8s_client = k8s_client
        self.mongo_client = mongo_client
        self.jobs_collection = mongo_client.ktqueue.jobs

    @convert_asyncio_task
    @apiauthenticated
    async def post(self):
        """
        Create a new job.
        e.x. request:
            {
                "name": "test-17",
                "command": "echo 'aW1wb3J0IHRlbnNvcmZsb3cgYXMgdGYKaW1wb3J0IHRpbWUKc2Vzc2lvbiA9IHRmLlNlc3Npb24oKQpmb3IgaSBpbiByYW5nZSg2MDApOgogICAgdGltZS5zbGVlcCgxKQogICAgcHJpbnQoaSkK' | base64 -d | python3",
                "gpuNum": 1,
                "image": "comzyh/tf_image",
                "repo": "https://github.com/comzyh/TF_Docker_Images.git",
                "commit_id": "3701b94219fb06974f485cabf99ad88019afe618"
            }
        """
        user = self.get_current_user()

        body_arguments = json.loads(self.request.body.decode('utf-8'))

        name = body_arguments.get('name')

        if len(name) > 58:  # kubernetes doesn't accept name longer than 64. 64 - 6 (pod name suffix) = 58
            self.set_status(400)
            self.finish({"message": "job name too long(>58)."})
            return

        if not self.__job_name_pattern.match(name):
            self.set_status(400)
            self.finish(
                {"message": "illegal task name, regex used for validation is [a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*"})
            return

        # job with same name is forbidden
        if self.jobs_collection.find_one({'name': name}):
            self.set_status(400)
            self.finish(json.dumps({'message': 'Job {} already exists'.format(name)}))
            return

        command = body_arguments.get('command')
        node = body_arguments.get('node', None)
        gpu_num = int(body_arguments.get('gpuNum'))
        image = body_arguments.get('image')
        repo = body_arguments.get('repo', None)
        branch = body_arguments.get('branch', None)
        commit_id = body_arguments.get('commit', None)
        comments = body_arguments.get('comments', None)
        mounts = body_arguments.get('volumeMounts', [])
        cpu_limit = body_arguments.get('cpuLimit', None)
        memory_limit = body_arguments.get('memoryLimit', None)
        auto_restart = body_arguments.get('autoRestart', False)

        job_dir = os.path.join('/cephfs/ktqueue/jobs/', name)

        job = generate_job(
            name=name, command=command, node=node, gpu_num=gpu_num, image=image,
            repo=repo, branch=branch, commit_id=commit_id, comments=comments,
            mounts=mounts, cpu_limit=cpu_limit, memory_limit=memory_limit,
            auto_restart=auto_restart
        )

        self.jobs_collection.update_one({'name': name}, {'$set': {
            'name': name,
            'node': node,
            'user': user,
            'command': command,
            'gpuNum': gpu_num,
            'repo': repo,
            'branch': branch,
            'commit': commit_id,
            'comments': comments,
            'image': image,
            'status': 'fetching',
            'tensorboard': False,
            'hide': False,
            'volumeMounts': mounts,
            'cpuLimit': cpu_limit,
            'memoryLimit': memory_limit,
        }}, upsert=True)
        self.finish(json.dumps({'message': 'job {} successful created.'.format(name)}))

        # clone code
        await clone_code(
            name=name, repo=repo, branch=branch, commit_id=commit_id,
            jobs_collection=self.jobs_collection, job_dir=job_dir,
            crediential=KTQueueDefaultCredentialProvider(repo=repo, user=user, mongo_client=self.mongo_client))

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
        page_size = int(self.get_argument('pageSize', 20))
        hide = self.get_argument('hide', None)
        fav = self.get_argument('fav', None)
        status = self.get_argument('status', None)
        tags = self.get_arguments('tag')
        user = self.get_arguments('user[]')
        node = self.get_arguments('node[]')
        searchJobName = self.get_argument('searchJobName', None)

        query = {}

        # hide
        if hide is None:  # default is False
            query['hide'] = False
        elif hide != 'all':  # 'all' means no filter
            query['hide'] = False if hide == '0' else True

        if searchJobName:
            query['name'] = re.compile(".*?%s.*?" %searchJobName, re.IGNORECASE)

        # tags
        if tags:
            query['tags': {'$all': tags}]

        # fav
        if fav:
            query['fav'] = True if fav == '1' else False

        # status; Running etc.
        if status:
            if status == '$RunningExtra':
                query.pop('hide', None)
                query['status'] = {'$nin': [
                    'Completed', 'ManualStop', 'FetchError', 
                    re.compile(".*?Failed.*?", re.IGNORECASE),
                    re.compile(".*?terminated.*?", re.IGNORECASE),
                ]}
            else:
                query['status'] = status
        # user
        if user:
            query['user'] = {'$in': user}

        # node
        if node:
            query['node'] = {'$in': node}

        if status == '$RunningExtra':
            query = {'$or': [query, {'tensorboard': True}]}

        count = self.jobs_collection.count(query)
        jobs = list(self.jobs_collection.find(query).sort("_id", -1).skip(page_size * (page - 1)).limit(page_size))
        for job in jobs:
            job['_id'] = str(job['_id'])
        self.finish(json.dumps({
            'page': page,
            'total': count,
            'pageSize': page_size,
            'data': jobs,
        }))

    @apiauthenticated
    async def put(self):
        """modify job.
            only part of fields can be modified.
        """
        body_arguments = json.loads(self.request.body.decode('utf-8'))

        allowedFields = ['hide', 'comments', 'tags', 'fav']
        job = self.jobs_collection.find_one({'_id': bson.ObjectId(body_arguments['_id'])})
        if job['status'] in ('ManualStop', 'Completed'):
            allowedFields += ['node', 'gpuNum', 'image', 'command', 'volumeMounts', 'cpuLimit', 'memoryLimit']
        update_data = {k: v for k, v in body_arguments.items() if k in allowedFields}
        self.jobs_collection.update_one({'_id': bson.ObjectId(body_arguments['_id'])}, {'$set': update_data})
        ret = self.jobs_collection.find_one({'_id': bson.ObjectId(body_arguments['_id'])})
        ret['_id'] = str(ret['_id'])
        self.finish(ret)


class JobLogVersionHandler(tornado.web.RequestHandler):

    def initialize(self, k8s_client):
        self.k8s_client = k8s_client

    @convert_asyncio_task
    async def get(self, job):
        from ktqueue.utils import get_log_versions
        versions = get_log_versions(job)
        pods = await self.k8s_client.call_api(
            method='GET',
            api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
            params={'labelSelector': 'job-name={job}'.format(job=job)}
        )
        if pods.get('items', None):
            versions = ['current'] + versions
        self.write({
            'job': job,
            'versions': versions
        })


class JobLogHandler(BaseHandler):

    def initialize(self, k8s_client, mongo_client):
        self.k8s_client = k8s_client
        self.mongo_client = mongo_client
        self.jobs_collection = mongo_client.ktqueue.jobs
        self.closed = False
        self.follow = False

    async def get_log_stream(self, job, version):
        pods = await self.k8s_client.call_api(
            method='GET',
            api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
            params={'labelSelector': 'job-name={job}'.format(job=job)}
        )
        if pods.get('items', None):
            params = {}
            timeout = 60
            if self.follow:
                params['follow'] = 'true'
                tailLines = self.get_argument('tailLines', None)
                if tailLines:
                    params['tailLines'] = tailLines
                timeout = 0  # disable timeout checks
            pod_name = pods['items'][0]['metadata']['name']
            resp = await self.k8s_client.call_api_raw(
                method='GET',
                api='/api/v1/namespaces/{namespace}/pods/{pod_name}/log'.format(namespace=settings.job_namespace, pod_name=pod_name),
                params=params, timeout=timeout
            )
            return resp
        return None

    @convert_asyncio_task
    async def get(self, job, version=None):
        if version and version != 'current':
            with open(os.path.join('/cephfs/ktqueue/logs', job, 'log.{version}.txt'.format(version=version)), 'rb') as f:
                self.finish(f.read())
            return
        self.follow = self.get_argument('follow', None) == 'true'
        resp = await self.get_log_stream(job, version)
        if resp and resp.status == 200:
            try:
                async for chunk in resp.content.iter_any():
                    if self.closed:
                        break
                    self.write(chunk)
                    if self.follow:
                        self.flush()
            finally:
                resp.close()

    def on_connection_close(self):
        self.closed = True


class JobLogWSHandler(tornado.websocket.WebSocketHandler, JobLogHandler):

    def initialize(self, *args, **kwargs):
        JobLogHandler.initialize(self, *args, **kwargs)

    def check_origin(self, origin):
        return True

    @convert_asyncio_task
    async def open(self, job):
        self.follow = True
        resp = await self.get_log_stream(job, 'current')
        if resp and resp.status == 200:
            try:
                async for chunk in resp.content.iter_any():
                    if self.closed:
                        break
                    self.write_message(chunk)
            except Exception as e:
                raise
            finally:
                resp.close()

    def on_close(self):
        self.closed = True

    def on_message(self):
        pass


class StopJobHandler(BaseHandler):

    def initialize(self, k8s_client, mongo_client):
        self.k8s_client = k8s_client
        self.mongo_client = mongo_client
        self.jobs_collection = mongo_client.ktqueue.jobs

    @convert_asyncio_task
    @apiauthenticated
    async def post(self, job):
        await k8s_delete_job(self.k8s_client, job)
        self.finish({'message': 'Job {} successful deleted.'.format(job)})

class RestartJobHandler(BaseHandler):

    def initialize(self, k8s_client, mongo_client):
        self.k8s_client = k8s_client
        self.mongo_client = mongo_client
        self.jobs_collection = mongo_client.ktqueue.jobs

    @convert_asyncio_task
    @apiauthenticated
    async def post(self, job):
        job_name = job
        await k8s_delete_job(self.k8s_client, job_name)
        job = defaultdict(lambda: None)
        job.update(self.jobs_collection.find_one({'name': job_name}))
        job_dir = os.path.join('/cephfs/ktqueue/jobs/', job['name'])

        job_description = generate_job(
            name=job['name'], command=job['command'], node=job['node'], gpu_num=job['gpuNum'], image=job['image'],
            repo=job['name'], branch=job['command'], commit_id=job['commit'], comments=job['comments'],
            mounts=job['volumeMounts'], cpu_limit=job['cpuLimit'], memory_limit=job['memoryLimit'],
        )

        if job['status'] == 'FetchError':
            self.jobs_collection.update_one({'name': job}, {'$set': {'status': 'fetching'}})

        self.finish({'message': 'job {} successful restarted.'.format(job['name'])})

        # Refetch
        if job['status'] == 'FetchError':
            await clone_code(
                name=job['name'], repo=job['repo'], branch=job['branch'], commit_id=job['commit'],
                jobs_collection=self.jobs_collection, job_dir=job_dir,
                crediential=KTQueueDefaultCredentialProvider(
                    repo=job['repo'], user=self.get_current_user(), mongo_client=self.mongo_client
                ))

        await self.k8s_client.call_api(
            api='/apis/batch/v1/namespaces/{namespace}/jobs'.format(namespace=settings.job_namespace),
            method='POST',
            data=job_description
        )


class TensorBoardHandler(BaseHandler):

    def initialize(self, k8s_client, mongo_client):
        self.k8s_client = k8s_client
        self.mongo_client = mongo_client
        self.jobs_collection = mongo_client.ktqueue.jobs

    @convert_asyncio_task
    @apiauthenticated
    async def post(self, job):
        body_arguments = json.loads(self.request.body.decode('utf-8'))
        logdir = body_arguments.get('logdir', '/cephfs/ktqueue/logs/{job}/train'.format(job=job))
        command = 'tensorboard --logdir {logdir} --host 0.0.0.0'.format(logdir=logdir)

        job_record = defaultdict(lambda: None)
        job_record.update(self.jobs_collection.find_one({'name': job}))
        job_description = generate_job(
            name=job_record['name'], command=command, node=job_record['node'], gpu_num=0, image=job_record['image'],
            repo=None, branch=None, commit_id=None, comments=None, mounts=job_record['volumeMounts'],
            cpu_limit=job_record['cpuLimit'], memory_limit=job_record['memoryLimit'],
            load_nvidia_driver=True,
        )
        pod_spec = dict(job_description['spec']['template']['spec'])
        pod_spec['containers'][0]['name'] = 'ktqueue-tensorboard'
        print(pod_spec)

        pod = {
            'apiVersion': 'v1',
            'kind': 'Pod',
            'metadata': {
                'name': '{job}-tensorboard'.format(job=job),
                'labels': {
                    'ktqueue-tensorboard-job-name': job
                }
            },
            'spec': pod_spec
        }

        ret = await self.k8s_client.call_api(
            api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
            method='POST',
            data=pod
        )
        if 'metadata' in ret and 'creationTimestamp' in ret['metadata']:
            self.jobs_collection.update_one({'name': job}, {'$set': {'tensorboard': True}})
        else:
            self.set_status(500)

        self.write(ret)

    @convert_asyncio_task
    @apiauthenticated
    async def delete(self, job):
        pods = await self.k8s_client.call_api(
            method='GET',
            api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
            params={'labelSelector': 'ktqueue-tensorboard-job-name={job}'.format(job=job)}
        )
        if pods.get('items', None):
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
