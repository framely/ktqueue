# encoding: utf-8
from .utils import BaseHandler
from .utils import apiauthenticated
import ktqueue.settings


class CurrentUserHandler(BaseHandler):
    @apiauthenticated
    def get(self):
        self.finish({
            'user': self.get_current_user(),
            'auth_required': ktqueue.settings.auth_required
        })

    def delete(self):
        self.clear_cookie('user')
        self.finish({
            'msg': 'ok'
        })
