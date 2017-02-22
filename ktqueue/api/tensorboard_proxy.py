# encoding: utf-
import tornado.web
import tornado.httpclient
import tornado.httputil
import urllib.parse
import re

from tornado.httpclient import HTTPRequest

job_tensorboard_map = {}


class TensorBoardProxyHandler(tornado.web.RequestHandler):
    __job_pattern = re.compile(r'/tensorboard/(?P<job>[\w_\-\.]+)/(.*?)')

    def initialize(self, client):
        self.client = client

    async def get(self, **kwargs):
        if 'job' not in kwargs:
            referer_path = urllib.parse.urlparse(self.request.headers['Referer']).path
            job = self.__job_pattern.match(referer_path).group('job')
            url = 'data/' + kwargs['url']
        else:
            job = kwargs['job']
            url = kwargs['url']

        host = job_tensorboard_map.get(job, None)
        if not host:
            self.set_status(404)
            self.finish({'message': 'tensorboard not found.'})
            return

        parsed_url = urllib.parse.urlparse(self.request.uri)
        if parsed_url.query:
            url += '?' + parsed_url.query

        body = self.request.body
        if not body:
            body = None

        request = HTTPRequest(
            url='http://{host}:6006/{url}'.format(host=host, url=url),
            method=self.request.method, body=body,
            headers=self.request.headers, follow_redirects=False,
            allow_nonstandard_methods=True,
            request_timeout=180 if 'job' not in kwargs else 4,
        )
        response = await self.client.fetch(request)

        if response.error and not isinstance(response.error, tornado.httpclient.HTTPError):
            self.set_status(500)
            self.finish('Internal server error:\n' + str(response.error))
            return

        self.set_status(response.code)
        self._headers = tornado.httputil.HTTPHeaders()
        for header, v in response.headers.get_all():
            if header not in ('Content-Length', 'Transfer-Encoding', 'Content-Encoding', 'Connection'):
                self.add_header(header, v)

        if response.body:
            self.set_header('Content-Length', len(response.body))
            self.write(response.body)

        self.finish()

    async def post(self, **kwargs):
        await self.get(**kwargs)
