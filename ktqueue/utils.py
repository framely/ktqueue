# encoding: utf-8
import os
import re
import logging
import smtplib

from email.mime.text import MIMEText

from ktqueue import settings
from .cloner import GitCredentialProvider


def get_log_versions(job_name):
    log_dir = os.path.join('/mnt/cephfs/ktqueue/logs', job_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    versions = []
    for filename in os.listdir(log_dir):
        group = re.match(r'log\.(?P<id>\d+)\.txt', filename)
        if group:
            versions.append(int(group.group('id')))
    return sorted(versions)


async def save_job_log(job_name, pod_name, k8s_client):
    log_dir = os.path.join('/mnt/cephfs/ktqueue/logs', job_name)
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
    await k8s_client.call_api(
        method='DELETE',
        params={'gracePeriodSeconds': 0},
        api='/apis/batch/v1/namespaces/{namespace}/jobs/{name}'.format(namespace=settings.job_namespace, name=job)
    )

    await k8s_client.call_api(
        api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
        method='PATCH',
        params={'labelSelector': 'job-name={job}'.format(job=job)},
        headers={'Content-Type': 'application/json-patch+json'},
        data=[{"op": "add", "path": "/metadata/labels/ktqueue-terminating", "value": "true"}]
    )

    if pod_name is None:
        pods = await k8s_client.call_api(
            method='GET',
            api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace),
            params={'labelSelector': 'job-name={job}'.format(job=job)}
        )
        if save_log and pods.get('items', None):
            for pod in pods["items"]:
                name = pod['metadata']['name']
                await save_job_log(job_name=job, pod_name=name, k8s_client=k8s_client)
        await k8s_client.call_api(
            method='DELETE',
            params={
                'labelSelector': 'job-name={job}'.format(job=job),
                'gracePeriodSeconds': 0,
            },
            api='/api/v1/namespaces/{namespace}/pods'.format(namespace=settings.job_namespace)
        )
    else:
        if save_log:
            await save_job_log(job_name=job, pod_name=pod_name, k8s_client=k8s_client)
        await k8s_client.call_api(
            method='DELETE',
            params={'gracePeriodSeconds': 0},
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


def send_email(message):
    if not settings.mail_receivers:
        return
    email_message = MIMEText(message, 'plain', 'utf-8')
    email_message['Subject'] = 'ktqueue report'
    email_message['From'] = settings.mail_user
    email_message['To'] = settings.mail_receivers[0]
    try:
        smtp_obj = smtplib.SMTP_SSL(settings.mail_host)
        smtp_obj.login(settings.mail_sender, settings.mail_password)
        smtp_obj.sendmail(settings.mail_sender, settings.mail_receivers, email_message.as_string())
        smtp_obj.quit()
    except smtplib.SMTPException as e:
        print('send email={mail_message} err '.format(mail_message = email_message.as_string()), e)
