import sys, os, base64
from io import BytesIO
from urllib.parse import urlencode

sys.path.insert(0, '/var/task')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_app = None

def get_app():
    global _app
    if _app is None:
        from app import app
        _app = app
    return _app

def handler(event, context):
    app = get_app()

    path = event.get('path') or '/'
    method = event.get('httpMethod', 'GET')
    headers = event.get('headers') or {}
    qs = event.get('queryStringParameters') or {}
    body = event.get('body') or b''
    is_b64 = event.get('isBase64Encoded', False)

    if isinstance(body, str):
        body = base64.b64decode(body) if is_b64 else body.encode('utf-8')

    query_string = urlencode(qs) if isinstance(qs, dict) else (qs or '')
    host = headers.get('host') or headers.get('Host') or 'localhost'

    environ = {
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'CONTENT_TYPE': headers.get('content-type') or headers.get('Content-Type') or '',
        'CONTENT_LENGTH': str(len(body)),
        'SERVER_NAME': host,
        'SERVER_PORT': '443',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'HTTP_HOST': host,
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https',
        'wsgi.input': BytesIO(body),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
    }

    for k, v in headers.items():
        key = 'HTTP_' + k.upper().replace('-', '_')
        if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
            environ[key] = v

    status_holder = {}
    resp_headers = {}

    def start_response(status, response_headers, exc_info=None):
        status_holder['code'] = int(status.split(' ', 1)[0])
        for k, v in response_headers:
            resp_headers[k] = v

    chunks = []
    result = app(environ, start_response)
    try:
        for chunk in result:
            chunks.append(chunk)
    finally:
        if hasattr(result, 'close'):
            result.close()

    body_bytes = b''.join(chunks)
    content_type = resp_headers.get('Content-Type', '')
    is_text = any(t in content_type for t in ('text', 'json', 'javascript', 'xml'))

    if is_text:
        return {
            'statusCode': status_holder.get('code', 200),
            'headers': resp_headers,
            'body': body_bytes.decode('utf-8', errors='replace'),
        }

    return {
        'statusCode': status_holder.get('code', 200),
        'headers': resp_headers,
        'body': base64.b64encode(body_bytes).decode('utf-8'),
        'isBase64Encoded': True,
    }
