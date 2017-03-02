# encoding: utf-8
from .utils import BaseHandler
import ktqueue.settings


class CurrentUserHandler(BaseHandler):

    def get(self):
        self.finish({
            'user': self.get_current_user(),
            'auth_required': ktqueue.settings.auth_required == '1'
        })
