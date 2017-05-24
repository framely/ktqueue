# encoding: utf-8
from .utils import BaseHandler


class AuthRequestHandler(BaseHandler):
    """Support Nginx auth_request directive.
    http://nginx.org/en/docs/http/ngx_http_auth_request_module.html
    """
    def get(self):
        if self.get_current_user():
            self.set_status(202)
        else:
            self.set_status(401)

    def head(self):
        self.get()
