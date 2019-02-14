import os

mongodb_server = os.environ.get('KTQ_MONGODB_SERVER', 'ktqueue-mongodb')
job_namespace = os.environ.get('KTQ_JOB_NAMESPACE', 'ktqueue')
auth_required = True if os.environ.get('KTQ_AUTH_REQUIRED', '0') == '1' else False
cookie_secret = os.environ.get('KTQ_COOKIE_SECRET', '')
oauth2_provider = os.environ.get('KTQ_OAUTH2_PROVIDER', 'github')
oauth2_clinet_id = os.environ.get('KTQ_OAUTH2_CLIENT_ID', '')
oauth2_client_secret = os.environ.get('KTQ_OAUTH2_CLIENT_SECRET', '')
oauth2_callback = os.environ.get('KTQ_OAUTH2_CALLBACK', None)
sfs_type = os.environ.get('KTQ_SHAREFS_TYPE', 'hostPath')
mail_receivers = [t for t in os.environ.get('KTQ_MAIL_USER', '').split('|') if '@' in t]

mail_host = 'smtp.gmail.com:465'
mail_user = 'ktqueue-amdin'
mail_sender = 'report.infra.01@naturali.io'
mail_password = 'report.infra.01::\"\"'

sfs_volume = {}
if sfs_type == 'hostPath':
    sfs_volume = {
        'name': 'cephfs',
        'hostPath': {
            'path': os.environ.get('KTQ_SHAREFS_HOSTPATH', '/mnt/cephfs')
        }
    }
elif sfs_type == 'azure_file':
    sfs_volume = {
        'name': 'cephfs',
        'azureFile': {
            'secretName': os.environ.get('KTQ_SHAREFS_AZURE_FILE_SECREAT_NAME'),
            'shareName': os.environ.get('KTQ_SHAREFS_AZURE_FILE_SHARE_NAME'),
            'readOnly': False,
        }
    }
elif sfs_type == 'nfs':
    sfs_volume = {
        'name': 'cephfs',
        'nfs': {
            'server': os.environ.get('KTQ_SHAREFS_NFS_SERVER'),
            'path': os.environ.get('KTQ_SHAREFS_NFS_PATH', '/'),
            'readOnly': False,
        }
    }
