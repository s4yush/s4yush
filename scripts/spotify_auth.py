import base64
import json
import urllib.parse
import urllib.request

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-recently-played user-top-read user-read-currently-playing"
AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"


def authorize_link(client_id: str) -> str:
    query = urllib.parse.urlencode(
        {"client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT_URI, "scope": SCOPES}
    )
    return f"{AUTHORIZE_URL}?{query}"


def extract_code(landing_url: str) -> str:
    return urllib.parse.parse_qs(urllib.parse.urlparse(landing_url).query)["code"][0]


def exchange(client_id: str, client_secret: str, code: str) -> dict:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode(
        {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI}
    ).encode()
    request = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> None:
    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    print("\nOpen this link, approve access, then copy the FULL address of the page you land on.")
    print("That page will fail to load - that is expected.\n")
    print(authorize_link(client_id), "\n")
    code = extract_code(input("Paste the full address here: ").strip())
    tokens = exchange(client_id, client_secret, code)
    print("\nSPOTIFY_REFRESH_TOKEN =", tokens["refresh_token"])


if __name__ == "__main__":
    main()
