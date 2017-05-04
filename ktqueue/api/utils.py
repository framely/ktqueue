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
        user = self.get_secure_cookie("user")
        if user:
            return user.decode('utf-8')
        if not ktqueue.settings.auth_required:
            return 'anonymous'
        return None
