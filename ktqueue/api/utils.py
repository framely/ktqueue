# encoding: utf-8
import asyncio
import functools


def convert_asyncio_task(method):
    """https://github.com/KeepSafe/aiohttp/issues/1176"""
    @functools.wraps(method)
    async def wrapper(self, *args, **kwargs):
        coro = method(self, *args, **kwargs)
        return await asyncio.get_event_loop().create_task(coro)
    return wrapper
