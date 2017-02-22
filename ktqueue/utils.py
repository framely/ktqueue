# encoding: utf-8
import os
import re
from ktqueue import settings


async def save_job_log(job_name, pod_name, k8s_client):
    log_dir = os.path.join('/cephfs/ktqueue/logs', job_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    resp = await k8s_client.call_api_raw(
        method='GET',
        api='/api/v1/namespaces/{namespace}/pods/{pod_name}/log'.format(namespace=settings.job_namespace, pod_name=pod_name)
    )
    log_path = os.path.join(log_dir, 'log.txt')

    # Rolling log
    if os.path.exists(log_path):
        max_id = 0
        for filename in os.listdir(log_dir):
            group = re.match(r'log\.(?P<id>\d+)\.log', filename)
            if group:
                max_id = max(max_id, int(group.group('id')))
        os.rename(log_path, os.path.join(log_dir, 'log.{}.txt'.format(max_id + 1)))

    with open(os.path.join(log_dir, 'log.txt'), 'wb') as f:
        async for chunk in resp.content.iter_any():
            f.write(chunk)
    resp.close()
