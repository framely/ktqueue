# encoding: utf-8

import json
import re

import bson
import tornado.web

from .utils import BaseHandler
from .utils import apiauthenticated


class ReposHandler(BaseHandler):

    __https_pattern = re.compile(r'https:\/\/(\w+@\w+)?[\w.\/\-+]*.git')
    __ssh_pattern = re.compile(r'\w+@[\w.]+:[\w-]+\/[\w\-+]+\.git')

    def initialize(self, mongo_client):
        self.mongo_client = mongo_client
        self.repos_collection = self.mongo_client.ktqueue.repos

    @apiauthenticated
    async def post(self):
        """create a credential for repo, support both ssh & https.
            ssh e.x.:
                {
                    "repo": "git@github.com:naturali/tensorflow.git",
                    "ssh_key": "<your private key content here>"
                }
            https e.x.:
                {
                    "repo": "git@github.com:naturali/tensorflow.git",
                    "username": "<your username>",
                    "password": "<your password>"
                }
            use deployment key with ssh is recommanded
        """
        body = json.loads(self.request.body.decode('utf-8'))
        repo = body['repo'].strip()
        if self.__ssh_pattern.match(repo):
            if body.get('ssh_key', None) is None:
                self.set_status(400)
                self.finish(json.dumps({'message': 'ssh_key must be provided.'}))
                return
        elif self.__https_pattern.match(repo):
            if body.get('username', None) is None or body.get('password', None) is None:
                self.set_status(400)
                self.finish(json.dumps({'message': 'username and password must be provided.'}))
                return
        else:
            self.set_status(400)
            self.finish(json.dumps({'message': 'illigal repo'}))
            return

        self.repos_collection.update_one({'repo': repo}, {'$set': body}, upsert=True)
        self.finish(json.dumps({'message': 'repo {} successful added.'.format(repo)}))

    async def get(self):
        page = int(self.get_argument('page', 1))
        page_size = int(self.get_argument('pageSize', 20))
        count = self.repos_collection.count()
        repos = []
        for repo in self.repos_collection.find().sort("_id", -1).skip(page_size * (page - 1)).limit(page_size):
            repos.append({
                '_id': str(repo['_id']),
                'repo': repo['repo']
            })
        self.finish(json.dumps({
            'page': page,
            'total': count,
            'pageSize': page_size,
            'data': repos,
        }))


class RepoHandler(BaseHandler):

    def initialize(self, mongo_client):
        self.mongo_client = mongo_client
        self.repos_collection = self.mongo_client.ktqueue.repos

    @apiauthenticated
    async def delete(self, id):
        print(id)
        self.repos_collection.delete_one({'_id': bson.ObjectId(id)})
        self.finish({'message': 'repos successful added.'})
