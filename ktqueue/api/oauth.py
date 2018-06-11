# encoding: utf-8
import urllib
import json
import logging
import tornado.web
import tornado.auth
import tornado.httpclient

import ktqueue.settings


class GithubOAuth2StartHandler(tornado.web.RequestHandler, tornado.auth.OAuth2Mixin):
    _OAUTH_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
    _OAUTH_ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'

    def initialize(self, mongo_client):
        self.mongo_client = mongo_client

    async def get(self):
        code = self.get_argument('code', None)
        if code:
            # get token
            client = self.get_auth_http_client()
            request = tornado.httpclient.HTTPRequest(
                url=self._OAUTH_ACCESS_TOKEN_URL,
                method='POST',
                body=urllib.parse.urlencode(dict(
                    client_id=ktqueue.settings.oauth2_clinet_id,
                    client_secret=ktqueue.settings.oauth2_client_secret,
                    code=code)),
                headers=dict(Accept="application/json")
            )
            resp = await client.fetch(request)
            resp = json.loads(resp.body.decode('utf-8'))
            access_token = resp.get('access_token', None)
            if not access_token:
                raise Exception('Can not get access_token')
            request = tornado.httpclient.HTTPRequest(
                url='https://api.github.com/user',
                headers={
                    'Authorization': 'token {token}'.format(token=access_token),
                    'Accept': "application/json",
                    'User-Agent': 'KTQueue API Client'
                })
            resp = await client.fetch(request, raise_error=False)
            if resp.code != 200:
                logging.warn(resp.body)
                raise Exception('Failed to get user info')
            resp = json.loads(resp.body.decode('utf-8'))
            data = {
                'provider': 'github',
                'id': resp['login'],
                'access_token': access_token,
                'data': resp
            }
            self.mongo_client.ktqueue.oauth.update_one(
                {'provider': 'github', 'id': resp['login']},
                {'$set': data},
                upsert=True
            )
            self.set_secure_cookie('user', resp['login'])
            self.redirect('/')
        else:
            await self.authorize_redirect(
                redirect_uri=ktqueue.settings.oauth2_callback,
                client_id=ktqueue.settings.oauth2_clinet_id,
                client_secret=ktqueue.settings.oauth2_client_secret,
                scope=['repo'],  # reuquest access to private repository
            )

        return


OAuth2Handler = GithubOAuth2StartHandler
