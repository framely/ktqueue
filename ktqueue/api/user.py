# encoding: utf-8
from .utils import BaseHandler


class CurrentUserHandler(BaseHandler):

    def get(self):
        self.finish({'user': self.get_current_user()})
