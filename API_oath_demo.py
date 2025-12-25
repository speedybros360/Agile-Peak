"""
strava_oauth_demo.py

- Opens Strava's OAuth authorize URL in your browser.
- Starts a temporary HTTP server to catch the redirect.
- Extracts the `code` from the callback URL.
- POSTs that code to Strava's /oauth/token endpoint.
"""

import http.server
import socketserver
import threading
import webbrowser
import urllib.parse
import requests
import sys

# -------------------- CONFIGURATION --------------------
CLIENT_ID     = "191750"
CLIENT_SECRET = "3e13fd5a395a1eabcd91980ae458e42787e52f00"
REDIRECT_URI  = "http://localhost:8000/exchange_token"
SCOPE         = "read"

# ----------------------------------------------------------------
class OAuthHandler(http.server.BaseHTTPRequestHandler):
    """Handles the callback from Strava."""
    # Shared variable to store the code
    auth_code = None

    def do_GET(self):
        """Parse query string and capture `code`."""
        parsed = urllib.parse.urlparse(self.path)
        qs     = urllib.parse.parse_qs(parsed.query)

        if "code" in qs:
            OAuthHandler.auth_code = qs["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1> OAuth code received you can close this tab.</h1>")
            # Stop the server after we got what we need
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1> No code found in query string.</h1>")

    def log_message(self, format, *args):
        """Suppress console logging for each request."""
        return

def start_http_server(port=8000):
    """Start a simple HTTP server in its own thread."""
    handler = OAuthHandler
    httpd   = socketserver.TCPServer(("localhost", port), handler)
    thread  = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd

# ----------------------------------------------------------------
def open_authorization_url():
    """Build and open the Strava OAuth URL."""
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "approval_prompt": "force",   # forces the consent screen each time
        "scope": SCOPE,
    }
    url = f"https://www.strava.com/oauth/authorize?{urllib.parse.urlencode(params)}"
    print(f"Opening browser to:\n  {url}\n")
    webbrowser.open(url, new=2)   # 2 = open in a new tab if possible

# ----------------------------------------------------------------
def exchange_code_for_token(code):
    """POST the code to Strava's token endpoint."""
    url = "https://www.strava.com/oauth/token"
    data = {
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code":          code,
        "grant_type":    "authorization_code",
    }
    print("\nExchanging code for access token...")
    resp = requests.post(url, data=data)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        print(f"❌ HTTP error: {e}")
        sys.exit(1)

    token_info = resp.json()
    print("\n✅ Token response:")
    for k, v in token_info.items():
        if isinstance(v, (int, float)):
            # Show human‑readable expiry
            if k == "expires_at":
                from datetime import datetime
                v = datetime.utcfromtimestamp(v).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"  {k:12}: {v}")

# ----------------------------------------------------------------
def main():
    # Step 1 – start the HTTP server that will receive the redirect
    httpd = start_http_server(port=8000)

    # Step 2 – open the browser for user to authorize
    open_authorization_url()

    print("Waiting for you to finish the authorization in your browser...")
    # The server thread will shut itself down once we get a code.
    httpd.serve_forever()

    # Step 3 – retrieve the captured code
    if OAuthHandler.auth_code is None:
        print("❌ No authorization code received.")
        sys.exit(1)

    print(f"\n📥 Received code: {OAuthHandler.auth_code}")

    # Step 4 – exchange it for an access token
    exchange_code_for_token(OAuthHandler.auth_code)

if __name__ == "__main__":
    main()