import http.server, socketserver, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
class H(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        t = super().guess_type(path)
        return 'text/html; charset=utf-8' if t == 'text/html' else t
with socketserver.TCPServer(("127.0.0.1", 8931), H) as httpd:
    httpd.serve_forever()
