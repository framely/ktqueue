# encoding: utf-8
import logging
import asyncio
import json

import pymongo

from ktqueue.utils import save_job_log
from ktqueue import settings


class EventWatcher:

    def __init__(self, k8s_client=None):
        assert k8s_client is not None
        self.k8s_client = k8s_client
        self.running = True

    async def poll(self, api, method='GET', callback=None, **kwargs):
        """
        This function will never return, await the future carefully.
        """
        assert callback is not None
        timeout = kwargs.pop('timeout', None)
        while self.running:
            try:
                session = self.k8s_client.new_connector_session()
                resp = await self.k8s_client.call_api_raw(
                    api=api, method=method, timeout=timeout, session=session, **kwargs)
                async for line in resp.content:
                    try:
                        await callback(json.loads(line.decode('utf-8')))
                    except Exception as e:
                        logging.exception(e)
                    else:
                        pass
            except Exception as e:
                logging.exception(e)
                await asyncio.sleep(1)
            finally:
                session.close()


async def watch_pod(k8s_client):
    from .api.tensorboard_proxy import job_tensorboard_map

    mongo_client = pymongo.MongoClient('ktqueue-mongodb')
    jobs_collection = mongo_client.ktqueue.jobs

    async def callback(event):
        labels = event['object']['metadata']['labels']
        if 'ktqueue-tensorboard-job-name' in labels:
            job_name = labels['ktqueue-tensorboard-job-name']
            hostIP = event['object']['status'].get('podIP', None)
            if event['type'] == 'DELETED':
                job_tensorboard_map.pop(job_name, None)
            elif hostIP:
                job_tensorboard_map[job_name] = hostIP
            return

        if 'job-name' not in labels:
            return
        job_name = labels['job-name']
        if not jobs_collection.find_one({'name': job_name}):
            return

        if event['object']['status']['phase'] == 'Pending':
            jobs_collection.update_one({'name': job_name}, {'$set': {'status': 'Pending'}})
            return

        state = event['object']['status']['containerStatuses'][0]['state']
        for k, v in state.items():
            status = (k, v.get('reason', None))
            status_str = '{}: {}'.format(*status)
            continue

        logging.info('Job {} enter state {}'.format(job_name, status_str))

        job_update = {
            'state': state
        }

        # update status
        if status == ('terminated', 'Completed'):
            job_update['status'] = 'Completed'
        elif status == ('running', None):
            job_update['status'] = 'Running'
        else:
            job_update['status'] = status_str

        # update Running Node
        if status[0] == 'terminated':
            job_update['runningNode'] = None
        elif event['object']['spec'].get('nodeName', None):
            job_update['runningNode'] = event['object']['spec']['nodeName']

        if jobs_collection.find_one({'name': job_name})['status'] != 'ManualStop':
            jobs_collection.update_one({'name': job_name}, {'$set': job_update})

        # When a job is successful finished, save log and do not watch it any more
        if status[0] == 'terminated':
            pod_name = event['object']['metadata']['name']

            # save log first
            await save_job_log(job_name=job_name, pod_name=pod_name, k8s_client=k8s_client)

            # set label 'ktqueue-watching' to 'false'
            # refer https://tools.ietf.org/html/rfc6902#appendix-A.1 to know more about json-patch
            if status == ('terminated', 'Completed'):
                await k8s_client.call_api(
                    api='/api/v1/namespaces/{namespace}/pods/{name}'.format(namespace=settings.job_namespace, name=pod_name),
                    method='PATCH',
                    headers={'Content-Type': 'application/json-patch+json'},
                    data=[{"op": "add", "path": "/metadata/labels/ktqueue-watching", "value": "false"}]
                )

    event_watcher = EventWatcher(k8s_client=k8s_client)

    await event_watcher.poll(
        api='/api/v1/watch/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
        method='GET',
        callback=callback,
        params={'labelSelector': 'ktqueue-watching!=false'}
    )
