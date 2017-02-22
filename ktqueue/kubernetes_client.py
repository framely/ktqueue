# encoding: utf-8
import os
import aiohttp
import kubernetes
import json
import ssl


class kubernetes_client:

    def __init__(self, config=None):
        if config is None:
            config = self.get_service_account_config()
        self.token = config.get('token', None)
        self.host = config['host']
        self.token = config.get('token', None)
        self.port = config.get('port', None)
        self.schema = config['schema']
        self.api_preifx = "{schema}://{host}:{port}".format(schema=self.schema, host=self.host, port=self.port)
        self.ca_crt = None
        self.session = self.new_connector_session()

    def new_connector_session(self):
        """
        1 TCPConnector can handle 20 connections by default.
        """
        if self.schema == 'https':
            self.ca_crt = kubernetes.config.incluster_config.SERVICE_CERT_FILENAME
            sslcontext = ssl.create_default_context(cafile=self.ca_crt)
            conn = aiohttp.TCPConnector(ssl_context=sslcontext)
        else:
            conn = aiohttp.TCPConnector()
        return aiohttp.ClientSession(connector=conn)

    @classmethod
    def get_service_account_config(cls):
        config = {
            'host': os.environ['KUBERNETES_SERVICE_HOST'],
            'port': os.environ['KUBERNETES_SERVICE_PORT'],
        }
        config['token'] = os.environ.get('KUBERNETES_API_ACCOUNT_TOKEN', None)  # Not official, for debug usage
        config['schema'] = os.environ.get('KUBERNETES_API_SCHEMA', 'https')  # Not official, for debug usage
        if config['token'] is None:
            with open(kubernetes.config.incluster_config.SERVICE_TOKEN_FILENAME, 'r') as f:
                config['token'] = f.read()
        return config

    async def call_api(self, api, method='GET', **kwargs):
        resp = await self.call_api_raw(api=api, method=method, **kwargs)
        return json.loads(await resp.text())

    async def call_api_raw(self, api, method='GET', **kwargs):
        session = kwargs.pop('session', self.session)
        url = self.api_preifx + api
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = 'Bearer {token}'.format(token=self.token)
        headers['Content-Type'] = headers.get('Content-Type', 'application/json')
        if 'data' in kwargs and (isinstance(kwargs['data'], dict) or isinstance(kwargs['data'], list)):
            kwargs['data'] = json.dumps(kwargs['data'])
        return await session.request(method, url, headers=headers, **kwargs)
