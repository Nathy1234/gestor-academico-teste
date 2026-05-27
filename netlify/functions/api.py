import sys, os

for _p in ['/var/task', os.path.dirname(os.path.abspath(__file__)), os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

import serverless_wsgi
from app import app

def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)
