# encoding: utf-8
import asyncio
import functools
import tornado.web

import ktqueue.settings


def convert_asyncio_task(method):
    """https://github.com/KeepSafe/aiohttp/issues/1176"""
    @functools.wraps(method)
    async def wrapper(self, *args, **kwargs):
        coro = method(self, *args, **kwargs)
        return await asyncio.get_event_loop().create_task(coro)
    return wrapper


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        try: user = self.get_secure_cookie("user")
        except: user = None
        if user:
            return user.decode('utf-8')
        if not ktqueue.settings.auth_required:
            return 'anonymous'
        return None


def apiauthenticated(method):
    """ Return 401 if user is not authenticated
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            raise tornado.web.HTTPError(401)
        return method(self, *args, **kwargs)
    return wrapper
