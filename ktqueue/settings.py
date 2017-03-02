import os

job_namespace = os.environ.get('KTQ_JOB_NAMESPACE', 'ktqueue')
auth_required = os.environ.get('KTQ_AUTH_REQUIRED', False)
cookie_secret = os.environ.get('KTQ_COOKIE_SECRET', '')
oauth2_provider = os.environ.get('KTQ_OAUTH2_PROVIDER', 'github')
oauth2_clinet_id = os.environ.get('KTQ_OAUTH2_CLIENT_ID', '')
oauth2_client_secret = os.environ.get('KTQ_OAUTH2_CLIENT_SECRET', '')
oauth2_callback = os.environ.get('KTQ_OAUTH2_CALLBACK', None)
