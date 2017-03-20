# encoding: utf-8
import os
import re
from ktqueue import settings


def get_log_versions(job_name):
    log_dir = os.path.join('/cephfs/ktqueue/logs', job_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    versions = []
    for filename in os.listdir(log_dir):
        group = re.match(r'log\.(?P<id>\d+)\.txt', filename)
        if group:
            versions.append(int(group.group('id')))
    return sorted(versions)


async def save_job_log(job_name, pod_name, k8s_client):
    log_dir = os.path.join('/cephfs/ktqueue/logs', job_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    resp = await k8s_client.call_api_raw(
        method='GET',
        api='/api/v1/namespaces/{namespace}/pods/{pod_name}/log'.format(namespace=settings.job_namespace, pod_name=pod_name)
    )

    max_version = 0
    for version in get_log_versions(job_name=job_name):
        max_version = max(max_version, int(version))
    log_path = os.path.join(log_dir, 'log.{}.txt'.format(max_version + 1))

    with open(log_path, 'wb') as f:
        async for chunk in resp.content.iter_any():
            f.write(chunk)
    resp.close()
