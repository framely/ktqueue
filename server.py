# encoding: utf-8
import asyncio
import os
import sys
import logging

import pymongo
import tornado
import tornado.web
import tornado.autoreload

from tornado.simple_httpclient import SimpleAsyncHTTPClient
from tornado.platform.asyncio import AsyncIOMainLoop

import ktqueue.settings
from ktqueue.kubernetes_client import kubernetes_client
from ktqueue.api import JobsHandler
from ktqueue.api import JobLogHandler
from ktqueue.api import JobLogWSHandler
from ktqueue.api import JobLogVersionHandler
from ktqueue.api import ReposHandler
from ktqueue.api import RepoHandler
from ktqueue.api import NodesHandler
from ktqueue.api import StopJobHandler
from ktqueue.api import RestartJobHandler
from ktqueue.api import TensorBoardProxyHandler
from ktqueue.api import TensorBoardHandler
from ktqueue.api import OAuth2Handler
from ktqueue.api import CurrentUserHandler
from ktqueue.api import AuthRequestHandler


from ktqueue.event_watcher import watch_pod

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

__frontend_path = os.path.join(BASE_DIR, 'frontend')
__dist_path = os.path.join(__frontend_path, 'dist')


def create_db_index():
    client = pymongo.MongoClient('ktqueue-mongodb')
    client.ktqueue.jobs.create_index([("name", pymongo.ASCENDING)], unique=True)
    client.ktqueue.jobs.create_index([("hide", pymongo.ASCENDING)])
    client.ktqueue.jobs.create_index([("status", pymongo.ASCENDING)])
    client.ktqueue.credentials.create_index([("repo", pymongo.ASCENDING)], unique=True)
    client.ktqueue.oauth.create_index([("provider", pymongo.ASCENDING), ("id", pymongo.ASCENDING)], unique=True)
    client.ktqueue.jobs.update_many({'hide': {'$exists': False}}, {'$set': {'hide': False}})
    client.ktqueue.jobs.update_many({'fav': {'$exists': False}}, {'$set': {'fav': False}})


def get_app():
    k8s_client = kubernetes_client()
    mongo_client = pymongo.MongoClient('ktqueue-mongodb')

    # other args to app
    app_kwargs = {}
    # debug
    app_kwargs['debug'] = os.environ.get('KTQUEUE_DEBUG', '0') == '1'
    # cookie_secret
    app_kwargs['cookie_secret'] = ktqueue.settings.cookie_secret
    application = tornado.web.Application([
        (r'/()', tornado.web.StaticFileHandler, {
            'path': __frontend_path,
            'default_filename': 'index.html'
        }),
        (r'/dist/(.*)', tornado.web.StaticFileHandler, {'path': __dist_path}),
        (r'/tensorboard/(?P<job>[\.\w_-]+)/(?P<url>.*)', TensorBoardProxyHandler, {'client': SimpleAsyncHTTPClient(max_clients=64)}),
        (r'/data/(?P<url>.*)', TensorBoardProxyHandler, {'client': SimpleAsyncHTTPClient(max_clients=64)}),  # This is a hack for TensorBoard
        (r'/auth/oauth2/start', OAuth2Handler, {'mongo_client': mongo_client}),
        (r'/auth/oauth2/callback', OAuth2Handler, {'mongo_client': mongo_client}),
        (r'/auth/auth', AuthRequestHandler),
        # APIS
        (r'/api/nodes', NodesHandler, {'k8s_client': k8s_client, 'mongo_client': mongo_client}),
        (r'/api/jobs', JobsHandler, {'k8s_client': k8s_client, 'mongo_client': mongo_client}),
        (r'/api/jobs/(?P<job>[\.\w_-]+)/log', JobLogHandler, {'k8s_client': k8s_client, 'mongo_client': mongo_client}),
        (r'/api/jobs/(?P<job>[\.\w_-]+)/log/(?P<version>\d+|current)', JobLogHandler, {'k8s_client': k8s_client, 'mongo_client': mongo_client}),
        (r'/api/jobs/(?P<job>[\.\w_-]+)/log/version', JobLogVersionHandler, {'k8s_client': k8s_client}),
        (r'/api/job/stop/(?P<job>[\.\w_\-]+)', StopJobHandler, {'k8s_client': k8s_client, 'mongo_client': mongo_client}),
        (r'/api/job/restart/(?P<job>[\.\w_-]+)', RestartJobHandler, {'k8s_client': k8s_client, 'mongo_client': mongo_client}),
        (r'/api/job/tensorboard/(?P<job>[\.\w_-]+)', TensorBoardHandler, {'k8s_client': k8s_client, 'mongo_client': mongo_client}),
        (r'/api/repos', ReposHandler, {'mongo_client': mongo_client}),
        (r'/api/repos/(?P<id>[0-9a-f]+)', RepoHandler, {'mongo_client': mongo_client}),
        (r'/api/current_user', CurrentUserHandler),
        (r'/wsapi/jobs/(?P<job>[\.\w_-]+)/log', JobLogWSHandler, {'k8s_client': k8s_client, 'mongo_client': mongo_client}),



    ], **app_kwargs)
    return application


async def async_init():
    tasks = [
        watch_pod(kubernetes_client()),
    ]
    await asyncio.wait(tasks)


def start_server():
    create_db_index()
    AsyncIOMainLoop().install()
    app = get_app()
    app.listen(8080)
    loop = asyncio.get_event_loop()
    if os.environ.get('KTQUEUE_DEBUG', '0') == '1':
        print('Reload.')
    loop.run_until_complete(async_init())
    loop.run_forever()


def main():
    logging.basicConfig(stream=sys.stdout, level=int(os.environ.get('KTQUEUE_DEBUG_LEVEL', logging.INFO)),
                        format='[%(asctime)s] %(name)s:%(levelname)s: %(message)s')
    start_server()


if __name__ == '__main__':
    main()
