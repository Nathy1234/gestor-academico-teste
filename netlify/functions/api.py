import sys, os

for _p in ['/var/task', os.path.dirname(os.path.abspath(__file__))]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

def handler(event, context):
    import serverless_wsgi
    from app import app
    return serverless_wsgi.handle_request(app, event, context)
