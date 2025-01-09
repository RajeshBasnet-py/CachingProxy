import os
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from cachetools import TTLCache
import argparse

# Cache configuration: store up to 100 items with a TTL of 300 seconds
cache = TTLCache(maxsize=100, ttl=300)

class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        path = self.path.lstrip('/')  # Remove leading slash
        
        # Include query parameters in the cache key
        cache_key = f"GET:{path}"
        
        # Check if the response is cached
        if cache_key in cache:
            # Cache HIT: return the cached response
            cached_response = cache[cache_key]
            self.send_response(cached_response['status_code'])
            self.send_header('Content-Type', cached_response['content_type'])
            self.send_header('X-Cache', 'HIT')
            for header, value in cached_response.get('headers', {}).items():
                self.send_header(header, value)
            self.end_headers()
            self.wfile.write(cached_response['content'])
            return

        # Cache MISS: forward the request to the origin server
        origin_server = os.getenv('ORIGIN_SERVER')
        if not origin_server:
            self.send_error(500, 'Origin server not specified.')
            return

        url = f"{origin_server}/{path}"
        try:
            # Forward the request to the origin server
            response = requests.get(url)

            # Create response to return to the client
            self.send_response(response.status_code)
            self.send_header('Content-Type', response.headers.get('Content-Type', ''))
            self.send_header('X-Cache', 'MISS')
            for header, value in response.headers.items():
                if header.lower() not in ['content-length', 'transfer-encoding', 'connection']:
                    self.send_header(header, value)
            self.end_headers()

            # Cache the response content
            content = response.content
            cache[cache_key] = {
                'status_code': response.status_code,
                'content': content,
                'content_type': response.headers.get('Content-Type', ''),
                'headers': {k: v for k, v in response.headers.items()}
            }
            self.wfile.write(content)

        except requests.exceptions.RequestException as e:
            self.send_error(500, f"Error: {str(e)}")

    def do_POST(self):
        """Handle POST requests (for completeness)."""
        self.send_error(405, "POST requests are not allowed in this proxy.")

def run_server(port, origin):
    """Start the proxy server."""
    os.environ['ORIGIN_SERVER'] = origin

    server_address = ('', port)
    httpd = HTTPServer(server_address, ProxyHTTPRequestHandler)
    print(f"Starting caching proxy server on port {port}, forwarding to {origin}")
    httpd.serve_forever()

def main():
    """Main function for argument parsing and starting the server."""
    parser = argparse.ArgumentParser(description='Start the caching proxy server')
    parser.add_argument('--port', type=int, required=False, help='Port to run the proxy server')
    parser.add_argument('--origin', type=str, required=False, help='Origin URL to forward requests to')
    parser.add_argument('--clear-cache', action='store_true', help='Clear the cache')

    args = parser.parse_args()

    if args.clear_cache:
        cache.clear()
        print("Cache cleared!")
        return

    if not args.port or not args.origin:
        print("Error: Both --port and --origin arguments are required unless clearing cache.")
        return

    run_server(args.port, args.origin)

if __name__ == '__main__':
    main()


# Imports:

# os: For setting environment variables.
# requests: To forward requests to the origin server
# BaseHTTPRequestHandler, HTTPServer: For handling HTTP requests and starting the server.
# TTLCache: To store and manage the cached responses.
# argparse: For command-line argument parsing.
# ProxyHTTPRequestHandler:

# This class extends BaseHTTPRequestHandler and handles GET requests by checking the cache first. If a cached response exists, it's returned with a header X-Cache: HIT. Otherwise, the request is forwarded to the origin server and the response is cached.
# Cache:

# The cache stores responses using TTLCache from the cachetools library, which limits the number of stored responses and assigns a time-to-live (TTL) for each cache entry.
# run_server:

# Starts the HTTP server on the specified port and forwards requests to the origin server.
# main:

# Parses the command-line arguments for --port, --origin, and --clear-cache. If --clear-cache is passed, the cache is cleared and the server does not start.