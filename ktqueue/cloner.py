# encoding: utf-8

import os
import hashlib
import re
import asyncio
import logging
import urllib.parse

import pymongo


class Cloner:
    """Do the git clone stuff in another thread"""

    __https_pattern = re.compile(r'https:\/\/(\w+@\w+)?[\w.\/\-+]*.git')
    __ssh_pattern = re.compile(r'\w+@[\w.]+:[\w-]+\/[\w\-+]+\.git')
    __ref_pattern = re.compile(r'(?P<hash>\w+)\s(?P<ref>[\w/\-]+)')

    def __init__(self, repo, dst_directory, branch=None, commit_id=None):
        self.repo = repo.strip()
        self.dst_directory = dst_directory
        self.branch = branch or 'master'
        self.commit_id = commit_id

        self.mongo_client = pymongo.MongoClient('ktqueue-mongodb')
        self.ssh_key_path = None
        self.repo_path = None
        self.repo_url = None

        if self.__ssh_pattern.match(repo):
            self.repo_type = 'ssh'
        elif self.__https_pattern.match(repo):
            self.repo_type = 'https'
        else:
            raise Exception('wrong repo type')

        if self.repo_type == 'ssh' and self.mongo_client.ktqueue.credentials.find_one({'repo': self.repo}) is None:
            raise Exception('ssh credential for {repo} must be provided.'.format(repo=repo))

        self.repo_hash = hashlib.sha1(self.repo.encode('utf-8')).hexdigest()

    async def prepare_ssh_key(self, repo):
        ssh_key_dir = os.path.join('/tmp/ktqueue/ssh_keys', self.repo_hash)
        if not os.path.exists(ssh_key_dir):
            os.makedirs(ssh_key_dir)
        self.ssh_key_path = os.path.join(ssh_key_dir, 'id')
        if not os.path.exists(self.ssh_key_path):
            with open(self.ssh_key_path, 'w') as f:
                credential = self.mongo_client.ktqueue.credentials.find_one({'repo': self.repo})
                f.write(credential['ssh_key'])
            os.chmod(self.ssh_key_path, 0o600)  # prevent WARNING: UNPROTECTED PRIVATE KEY FILE!
            await asyncio.sleep(1.0)  # os.chmod may have strange behavior, that ssh still permission 644 after too short time

    @classmethod
    async def git_with_ssh_key(cls, ssh_key_path, args, cwd=None):
        env = {**os.environ,
               'GIT_SSH_COMMAND': 'ssh -oStrictHostKeyChecking=no -i {ssh_key_path}'.format(ssh_key_path=ssh_key_path)
               }
        proc = await asyncio.create_subprocess_exec(*['git'] + args, stdout=asyncio.subprocess.PIPE, env=env, cwd=cwd)
        lines = []
        async for line in proc.stdout:
            logging.debug(line)
            lines.append(line)
        recode = await proc.wait()
        return recode, lines

    @classmethod
    def add_credential_to_https_url(cls, url, username, password):
        parsed = urllib.parse.urlparse(url)
        if username is not None and password is not None:
            host_and_port = parsed.hostname
            if parsed.port:
                host_and_port += ':' + parsed.port
            parsed._replace(netloc='{}:{}@{}'.format(username, password, host_and_port))
        return parsed.geturl()

    @classmethod
    async def git_with_https(cls, args, cwd=None):
        proc = await asyncio.create_subprocess_exec(*['git'] + args, stdout=asyncio.subprocess.PIPE, cwd=cwd)
        lines = []
        async for line in proc.stdout:
            logging.debug(line)
            lines.append(line)
        recode = await proc.wait()
        return recode, lines

    async def get_heads(self):
        proc = await asyncio.create_subprocess_exec(*['git', 'show-ref'], stdout=asyncio.subprocess.PIPE, cwd=self.repo_path)
        heads = {}
        async for line in proc.stdout:
            logging.debug(line)
            group = self.__ref_pattern.search(line.decode())
            if group:
                heads[group.group('ref')] = group.group('hash')
        return heads

    async def clone(self):
        if self.repo_type == 'ssh':
            retcode, retlines = await self.git_with_ssh_key(
                ssh_key_path=self.ssh_key_path,
                cwd='/cephfs/ktqueue/repos',
                args=['clone', self.repo, '--recursive', self.repo_hash],

            )
        else:
            retcode, retlines = await self.git_with_https(
                cwd='/cephfs/ktqueue/repos',
                args=['clone', self.repo_url, '--recursive', self.repo_hash],
            )
        if retcode != 0:
            raise Exception('clone repo failed with retcode {}.'.format(retcode))

    async def fetch(self):
        if self.repo_type == 'ssh':
            retcode, retlines = await self.git_with_ssh_key(
                ssh_key_path=self.ssh_key_path,
                cwd=self.repo_path,
                args=['fetch'],
            )
        else:
            retcode, retlines = await self.git_with_https(
                cwd=self.repo_path,
                args=['fetch'],
            )
        if retcode != 0:
            logging.error('fetch repo failed with retcode {}.'.format(retcode))

    async def clone_and_copy(self, archive_file=None, keep_archive=False):
        if not os.path.exists('/cephfs/ktqueue/repos'):
            os.makedirs('/cephfs/ktqueue/repos')
        self.repo_path = os.path.join('/cephfs/ktqueue/repos', self.repo_hash)

        if self.repo_type == 'ssh':
            await self.prepare_ssh_key(self.repo)
        elif self.repo_type == 'https':
            credential = self.mongo_client.ktqueue.credentials.find_one({'repo': self.repo})
            self.repo_url = self.repo
            if credential:
                self.repo_url = self.add_credential_to_https_url(
                    self.repo, username=credential['username'], password=credential['password'])

        if not os.path.exists(self.repo_path):  # Then clone it
            await self.clone()
        else:
            await self.fetch()

        # get commit_id
        if not self.commit_id and self.branch:
            heads = await self.get_heads()
            self.commit_id = heads.get('refs/remotes/origin/{branch}'.format(branch=self.branch), None)
            if not self.commit_id:
                raise Exception('Branch {branch} not found for {repo}.'.format(branch=self.branch, repo=self.repo))

        if not os.path.exists('/cephfs/ktqueue/repo_archive'):
            os.makedirs('/cephfs/ktqueue/repo_archive')
        if archive_file is None:
            archive_file = '/cephfs/ktqueue/repo_archive/{}.tar.gz'.format(self.commit_id)

        # Arcive commit_id
        logging.info('Arciving {}:{}'.format(self.repo, self.commit_id))
        with open(archive_file, 'wb') as f:
            proc = await asyncio.create_subprocess_exec(*['git', 'archive', self.commit_id, '--format', 'tar.gz'],
                                                        stdout=f, cwd=self.repo_path)
            retcode = await proc.wait()
            if retcode != 0:
                logging.error('Arcive repo failed with retcode {}'.format(retcode))

        if not os.path.exists(self.dst_directory):
            os.makedirs(self.dst_directory)
        proc = await asyncio.create_subprocess_exec(*['tar', 'xzf', archive_file], cwd=self.dst_directory)
        retcode = await proc.wait()

        if not keep_archive:
            os.remove(archive_file)
