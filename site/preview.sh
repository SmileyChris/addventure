#!/bin/sh
# Build and preview the full site
cd "$(dirname "$0")"
[ -d build ] || ./build.sh
port="${1:-8000}"
python3 -c "
import http.server, socketserver, os, sys, webbrowser, threading
os.chdir('build')
socketserver.TCPServer.allow_reuse_address = True
try:
    with socketserver.TCPServer(('', $port), http.server.SimpleHTTPRequestHandler) as s:
        print(f'Serving at http://localhost:$port')
        threading.Timer(0.5, webbrowser.open, args=[f'http://localhost:$port']).start()
        s.serve_forever()
except OSError:
    sys.exit(f'Error: port $port is already in use')
except KeyboardInterrupt:
    pass
"
