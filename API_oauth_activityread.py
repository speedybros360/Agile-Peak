import http.server
import socketserver
import threading
import webbrowser
import urllib.parse
import requests
import sys
import json
from pathlib import Path

# -------------------- CONFIGURATION --------------------
CLIENT_ID     = "191750"
CLIENT_SECRET = "3e13fd5a395a1eabcd91980ae458e42787e52f00"
REDIRECT_URI  = "http://localhost:8000/exchange_token"
SCOPE         = "activity:read_all"          # <-- changed scope

TOKEN_FILE    = Path(__file__).parent / "json_dump/token.json"

# ----------------------------------------------------------------
class OAuthHandler(http.server.BaseHTTPRequestHandler):
    """Handles the callback from Strava."""
    auth_code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs     = urllib.parse.parse_qs(parsed.query)

        if "code" in qs:
            OAuthHandler.auth_code = qs["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1> OAuth code received you may close this tab.</h1>")
            # Shut down the server in a background thread
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1> No code found in query string.</h1>")

    def log_message(self, format, *args):
        return

def start_http_server(port=8000):
    handler = OAuthHandler
    httpd   = socketserver.TCPServer(("localhost", port), handler)
    thread  = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd

# ----------------------------------------------------------------
def open_authorization_url():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "approval_prompt": "force",
        "scope": SCOPE,
    }
    url = f"https://www.strava.com/oauth/authorize?{urllib.parse.urlencode(params)}"
    print(f"Opening browser to:\n  {url}\n")
    webbrowser.open(url, new=2)

# ----------------------------------------------------------------
def exchange_code_for_token(code):
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
            if k == "expires_at":
                from datetime import datetime
                v = datetime.utcfromtimestamp(v).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"  {k:12}: {v}")

    # Store only the three pieces of data we need for future calls
    minimal = {
        "access_token":  token_info["access_token"],
        "refresh_token": token_info["refresh_token"],
        "expires_at":    token_info["expires_at"],
    }
    TOKEN_FILE.write_text(json.dumps(minimal, indent=2))
    print(f"\n✅ Tokens written to {TOKEN_FILE}")

# ----------------------------------------------------------------
def main():
    httpd = start_http_server(port=8000)
    open_authorization_url()

    print("Waiting for you to finish the authorization in your browser...")
    httpd.serve_forever()

    if OAuthHandler.auth_code is None:
        print("❌ No authorization code received.")
        sys.exit(1)

    print(f"\n📥 Received code: {OAuthHandler.auth_code}")
    exchange_code_for_token(OAuthHandler.auth_code)

if __name__ == "__main__":
    main()