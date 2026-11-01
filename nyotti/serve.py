"""Serve the static viewer from site/ on localhost."""
import functools
import http.server
import webbrowser

from .paths import ROOT


def run(port=4343, open_browser=True):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'site'))
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    url = f'http://127.0.0.1:{port}/'
    print(f'nyotti-xray viewer on {url}  (ctrl+c to stop)')
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
