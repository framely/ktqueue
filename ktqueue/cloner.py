# encoding: utf-8

import os
import hashlib
import re
import asyncio
import logging
import urllib.parse


class GitCredentialProvider:
    __https_pattern = re.compile(r'https:\/\/(\w+@\w+)?[\w.\/\-+]*.git')
    __ssh_pattern = re.compile(r'\w+@[\w.]+:[\w-]+\/[\w\-+]+\.git')

    @classmethod
    def get_repo_type(cls, repo):
        if cls.__ssh_pattern.match(repo):
            return 'ssh'
        elif cls.__https_pattern.match(repo):
            return'https'
        return None

    def __init__(self, ssh_key=None, https_username=None, https_password=None):
        pass

    @property
    def ssh_key(self):
        raise NotImplementedError

    @property
    def https_username(self):
        raise NotImplementedError

    @property
    def https_password(self):
        raise NotImplementedError


class Cloner:
    """Do the git clone stuff in another thread"""

    __ref_pattern = re.compile(r'(?P<hash>\w+)\s(?P<ref>[\w/\-]+)')

    def __init__(self, repo, dst_directory, branch=None, commit_id=None,
                 crediential=None):
        """Init
            crediential: a credientialProvider instance
        """
        self.repo = repo.strip()
        self.dst_directory = dst_directory
        self.branch = branch or 'master'
        self.commit_id = commit_id
        self.crediential = crediential

        self.ssh_key_path = None
        self.repo_path = None
        self.repo_url = None
        self.repo_type = GitCredentialProvider.get_repo_type(self.repo)

        if not self.repo_type:
            raise Exception('wrong repo type')

        if self.repo_type == 'ssh' and self.crediential.ssh_key is None:
            raise Exception('ssh credential for {repo} must be provided.'.format(repo=repo))

        self.repo_hash = hashlib.sha1(self.repo.encode('utf-8')).hexdigest()

    async def prepare_ssh_key(self, repo):
        ssh_key_dir = os.path.join('/tmp/ktqueue/ssh_keys', self.repo_hash)
        if not os.path.exists(ssh_key_dir):
            os.makedirs(ssh_key_dir)
        self.ssh_key_path = os.path.join(ssh_key_dir, 'id')
        if not os.path.exists(self.ssh_key_path):
            with open(self.ssh_key_path, 'w') as f:
                f.write(self.crediential.ssh_key)
            os.chmod(self.ssh_key_path, 0o600)  # prevent WARNING: UNPROTECTED PRIVATE KEY FILE!
            await asyncio.sleep(1.0)  # os.chmod may have strange behavior, that ssh still permission 644 after too short time

    @classmethod
    async def git_with_ssh_key(cls, ssh_key_path, args, cwd=None):
        env = {**os.environ,
               'GIT_SSH_COMMAND': 'ssh -oStrictHostKeyChecking=no -i {ssh_key_path}'.format(ssh_key_path=ssh_key_path)
               }
        proc = await asyncio.create_subprocess_exec(
            *['git'] + args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=env, cwd=cwd)
        lines = []
        async for line in proc.stdout:
            logging.debug(line)
            lines.append(line.decode())
        recode = await proc.wait()
        return recode, lines

    @classmethod
    def add_credential_to_https_url(cls, url, username, password):
        parsed = urllib.parse.urlparse(url)
        if username is not None:
            host_and_port = parsed.hostname
            if parsed.port:
                host_and_port += ':' + parsed.port
            if password:
                parsed = parsed._replace(netloc='{}:{}@{}'.format(username, password, host_and_port))
            else:
                parsed = parsed._replace(netloc='{}@{}'.format(username, host_and_port))
        return parsed.geturl()

    @classmethod
    async def git_with_https(cls, args, cwd=None):
        proc = await asyncio.create_subprocess_exec(
            *['git'] + args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, cwd=cwd)
        lines = []
        async for line in proc.stdout:
            logging.debug(line)
            lines.append(line.decode())

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
            logging.error('\n'.join(retlines))
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
                args=['fetch', self.repo_url, '+refs/heads/*:refs/remotes/origin/*'],
            )
        if retcode != 0:
            logging.error('\n'.join(retlines))
            logging.error('fetch repo failed with retcode {}.'.format(retcode))

    async def clone_and_copy(self, archive_file=None, keep_archive=False):
        if not os.path.exists('/cephfs/ktqueue/repos'):
            os.makedirs('/cephfs/ktqueue/repos')
        self.repo_path = os.path.join('/cephfs/ktqueue/repos', self.repo_hash)

        if self.repo_type == 'ssh':
            await self.prepare_ssh_key(self.repo)
        elif self.repo_type == 'https':
            self.repo_url = self.repo
            if self.crediential.https_username:
                self.repo_url = self.add_credential_to_https_url(
                    self.repo, username=self.crediential.https_username, password=self.crediential.https_password)

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
