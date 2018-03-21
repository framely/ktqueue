# encoding: utf-8
import os
import re
import logging

from ktqueue import settings
from .cloner import GitCredentialProvider


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
    logging.info('save log for {}, resp.status = {}'.format(job_name, resp.status))
    if resp.status > 300:
        resp.close()
        return

    max_version = 0
    for version in get_log_versions(job_name=job_name):
        max_version = max(max_version, int(version))
    log_path = os.path.join(log_dir, 'log.{}.txt'.format(max_version + 1))

    with open(log_path, 'wb') as f:
        async for chunk in resp.content.iter_any():
            f.write(chunk)
    resp.close()


async def k8s_delete_job(k8s_client, job, pod_name=None, save_log=True):
    if not pod_name:
        pods = await k8s_client.call_api(
            method='GET',
            api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
            params={'labelSelector': 'job-name={job}'.format(job=job)}
        )
        if pods.get('items', None):
            pod_name = pods['items'][0]['metadata']['name']
        else:
            return

    if save_log:
        await save_job_log(job_name=job, pod_name=pod_name, k8s_client=k8s_client)

    await k8s_client.call_api(
        api='/api/v1/namespaces/{namespace}/pods/{name}'.format(namespace=settings.job_namespace, name=pod_name),
        method='PATCH',
        headers={'Content-Type': 'application/json-patch+json'},
        data=[{"op": "add", "path": "/metadata/labels/ktqueue-terminating", "value": "true"}]
    )

    await k8s_client.call_api(
        method='DELETE',
        api='/apis/batch/v1/namespaces/{namespace}/jobs/{name}?gracePeriodSeconds={grace_seconds}'.format(namespace=settings.job_namespace, name=job, grace_seconds=0)
    )
    await k8s_client.call_api(
        method='DELETE',
        api='/api/v1/namespaces/{namespace}/pods/{name}'.format(namespace=settings.job_namespace, name=pod_name)
    )


class KTQueueDefaultCredentialProvider(GitCredentialProvider):
    """Give the authorization method for a (user, repo) combination

    default is use Github Oauth2,
    if repo authorization type is provided, use the spcific metho
    """
    allowed_method = ['none', 'github_oauth', 'ssh_key', 'https_password']

    def __init__(self, repo, user, mongo_client):
        self.repo = repo
        self.user = user
        self.mongo_client = mongo_client

        self.repos_collection = self.mongo_client.ktqueue.repos
        self.oauth_collection = self.mongo_client.ktqueue.oauth

        self._auth_type = 'none'
        if settings.auth_required:
            self._auth_type = 'github_oauth'
        self._ssh_key = None
        self._https_username = None
        self._https_password = None
        self.repo_type = None

    def prepare_credential(self):
        self.repo_type = self.get_repo_type(self.repo)
        repo = self.repos_collection.find_one({'repo': self.repo})
        if repo:
            self._auth_type = repo['authType']

        if self._auth_type == 'none':  # username = password = None
            pass
        elif self._auth_type == 'github_oauth':
            crediential = self.oauth_collection.find_one({'provider': 'github', 'id': self.user})
            if crediential:
                self._https_username = crediential['access_token']
        elif self._auth_type == 'ssh_key':
            self._ssh_key = repo['crediential']['sshKey']
        elif self._auth_type == 'https_password':
            self._https_username = repo['crediential']['username']
            self._https_password = repo['crediential']['password']

    @property
    def ssh_key(self):
        if not self._ssh_key:
            self.prepare_credential()
        return self._ssh_key

    @property
    def https_username(self):
        if not self._https_username:
            self.prepare_credential()
        return self._https_username

    @property
    def https_password(self):
        if not self._https_password:
            self.prepare_credential()
        return self._https_password
