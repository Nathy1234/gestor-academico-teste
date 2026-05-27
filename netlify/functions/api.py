import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import serverless_wsgi
from app import app

def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)
