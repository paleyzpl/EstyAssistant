import base64
import hashlib
import json
import logging
import secrets
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

logger = logging.getLogger(__name__)

ETSY_AUTH_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
ETSY_API_BASE = "https://api.etsy.com/v3/application"

DEFAULT_CREDENTIALS_PATH = Path.home() / ".etsy-assistant" / "credentials.json"
DEFAULT_SCOPES = "listings_w shops_r"

# Etsy taxonomy ID for "Prints" under Art & Collectibles > Prints
# This is a reasonable default for printable wall art
DEFAULT_TAXONOMY_ID = 1


@dataclass
class EtsyCredentials:
    api_key: str
    access_token: str
    refresh_token: str
    user_id: str
    shop_id: str | None = None

    def save(self, path: Path | None = None) -> Path:
        path = path or DEFAULT_CREDENTIALS_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "api_key": self.api_key,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "user_id": self.user_id,
            "shop_id": self.shop_id,
        }, indent=2) + "\n")
        path.chmod(0o600)
        logger.info("Credentials saved to %s", path)
        return path

    @classmethod
    def load(cls, path: Path | None = None) -> "EtsyCredentials":
        path = path or DEFAULT_CREDENTIALS_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"No credentials found at {path}. Run 'etsy-assistant auth' first."
            )
        data = json.loads(path.read_text())
        return cls(**data)


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def authorize(api_key: str, port: int = 5555) -> EtsyCredentials:
    """Run the OAuth 2.0 PKCE flow for Etsy.

    Opens a browser for user authorization and starts a local HTTP server
    to receive the callback.

    Args:
        api_key: Etsy API key (client_id).
        port: Local port for the OAuth callback server.

    Returns:
        EtsyCredentials with access and refresh tokens.
    """
    verifier, challenge = _generate_pkce()
    state = secrets.token_urlsafe(16)
    redirect_uri = f"http://localhost:{port}/callback"

    auth_params = urlencode({
        "response_type": "code",
        "client_id": api_key,
        "redirect_uri": redirect_uri,
        "scope": DEFAULT_SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"{ETSY_AUTH_URL}?{auth_params}"

    # Capture the authorization code via a local HTTP server
    auth_code = None
    received_state = None

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code, received_state
            query = parse_qs(urlparse(self.path).query)
            auth_code = query.get("code", [None])[0]
            received_state = query.get("state", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            if auth_code:
                self.wfile.write(b"<h1>Authorization successful!</h1>"
                                 b"<p>You can close this tab and return to the terminal.</p>")
            else:
                error = query.get("error", ["unknown"])[0]
                self.wfile.write(f"<h1>Authorization failed: {error}</h1>".encode())

        def log_message(self, format, *args):
            logger.debug(format, *args)

    logger.info("Opening browser for Etsy authorization...")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", port), CallbackHandler)
    server.timeout = 120
    server.handle_request()
    server.server_close()

    if not auth_code:
        raise RuntimeError("Authorization failed: no authorization code received")

    if received_state != state:
        raise RuntimeError("Authorization failed: state mismatch (possible CSRF)")

    # Exchange authorization code for tokens
    logger.info("Exchanging authorization code for tokens...")
    with httpx.Client() as http:
        resp = http.post(
            ETSY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": api_key,
                "redirect_uri": redirect_uri,
                "code": auth_code,
                "code_verifier": verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        token_data = resp.json()

    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]

    # Access token format is "userID.token" — extract user ID
    user_id = access_token.split(".")[0] if "." in access_token else ""

    creds = EtsyCredentials(
        api_key=api_key,
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user_id,
    )

    # Fetch shop ID
    shop_id = _get_shop_id(creds)
    if shop_id:
        creds = EtsyCredentials(
            api_key=creds.api_key,
            access_token=creds.access_token,
            refresh_token=creds.refresh_token,
            user_id=creds.user_id,
            shop_id=shop_id,
        )

    return creds


def refresh_access_token(creds: EtsyCredentials) -> EtsyCredentials:
    """Refresh an expired access token."""
    with httpx.Client() as http:
        resp = http.post(
            ETSY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": creds.api_key,
                "refresh_token": creds.refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        token_data = resp.json()

    return EtsyCredentials(
        api_key=creds.api_key,
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        user_id=token_data["access_token"].split(".")[0],
        shop_id=creds.shop_id,
    )


def _api_headers(creds: EtsyCredentials) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {creds.access_token}",
        "x-api-key": creds.api_key,
    }


def _get_shop_id(creds: EtsyCredentials) -> str | None:
    """Fetch the user's shop ID."""
    with httpx.Client() as http:
        resp = http.get(
            f"{ETSY_API_BASE}/users/{creds.user_id}/shops",
            headers=_api_headers(creds),
        )
        if resp.status_code == 200:
            data = resp.json()
            shops = data.get("results", [])
            if shops:
                return str(shops[0]["shop_id"])
    return None


def _request_with_refresh(
    creds: EtsyCredentials,
    method: str,
    url: str,
    creds_path: Path | None = None,
    **kwargs,
) -> httpx.Response:
    """Make an API request, auto-refreshing the token on 401."""
    with httpx.Client() as http:
        resp = http.request(method, url, headers=_api_headers(creds), **kwargs)

        if resp.status_code == 401:
            logger.info("Access token expired, refreshing...")
            creds = refresh_access_token(creds)
            creds.save(creds_path)
            resp = http.request(method, url, headers=_api_headers(creds), **kwargs)

        resp.raise_for_status()
        return resp


@dataclass(frozen=True)
class DraftListing:
    listing_id: str
    title: str
    url: str | None = None


def create_draft_listing(
    creds: EtsyCredentials,
    title: str,
    description: str,
    tags: list[str],
    price: float,
    taxonomy_id: int = DEFAULT_TAXONOMY_ID,
    creds_path: Path | None = None,
) -> DraftListing:
    """Create a draft digital download listing on Etsy.

    Args:
        creds: Authenticated Etsy credentials.
        title: Listing title (max 140 chars).
        description: Listing description.
        tags: List of search tags (max 13, each max 20 chars).
        price: Price in shop currency.
        taxonomy_id: Etsy taxonomy ID for the listing category.
        creds_path: Path to credentials file (for auto-refresh).

    Returns:
        DraftListing with the new listing ID.
    """
    if not creds.shop_id:
        raise ValueError("No shop_id in credentials. Re-run 'etsy-assistant auth'.")

    url = f"{ETSY_API_BASE}/shops/{creds.shop_id}/listings"
    data = {
        "quantity": 999999,
        "title": title[:140],
        "description": description,
        "price": price,
        "who_made": "i_did",
        "when_made": "made_to_order",
        "taxonomy_id": taxonomy_id,
        "type": "download",
        "tags": ",".join(tags[:13]),
    }

    logger.info("Creating draft listing: %s", title[:60])
    resp = _request_with_refresh(creds, "POST", url, creds_path, data=data)
    result = resp.json()

    listing_id = str(result["listing_id"])
    listing_url = result.get("url")
    logger.info("Created draft listing %s", listing_id)

    return DraftListing(listing_id=listing_id, title=title, url=listing_url)


def upload_listing_image(
    creds: EtsyCredentials,
    listing_id: str,
    image_path: Path,
    creds_path: Path | None = None,
) -> str:
    """Upload a preview image for a listing.

    Returns the listing_image_id.
    """
    if not creds.shop_id:
        raise ValueError("No shop_id in credentials.")

    url = f"{ETSY_API_BASE}/shops/{creds.shop_id}/listings/{listing_id}/images"
    image_path = Path(image_path)

    logger.info("Uploading preview image: %s", image_path.name)
    with open(image_path, "rb") as f:
        resp = _request_with_refresh(
            creds, "POST", url, creds_path,
            files={"image": (image_path.name, f, "image/png")},
        )

    result = resp.json()
    image_id = str(result["listing_image_id"])
    logger.info("Uploaded image %s for listing %s", image_id, listing_id)
    return image_id


def upload_listing_file(
    creds: EtsyCredentials,
    listing_id: str,
    file_path: Path,
    creds_path: Path | None = None,
) -> str:
    """Upload a digital download file for a listing.

    Returns the listing_file_id.
    """
    if not creds.shop_id:
        raise ValueError("No shop_id in credentials.")

    url = f"{ETSY_API_BASE}/shops/{creds.shop_id}/listings/{listing_id}/files"
    file_path = Path(file_path)

    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb > 20:
        raise ValueError(f"File too large ({size_mb:.1f} MB). Etsy limit is 20 MB per file.")

    logger.info("Uploading digital file: %s (%.1f MB)", file_path.name, size_mb)
    with open(file_path, "rb") as f:
        resp = _request_with_refresh(
            creds, "POST", url, creds_path,
            files={"file": (file_path.name, f, "application/octet-stream")},
        )

    result = resp.json()
    file_id = str(result["listing_file_id"])
    logger.info("Uploaded file %s for listing %s", file_id, listing_id)
    return file_id


# ── Web-compatible functions (bytes-based, no filesystem) ──

def build_auth_url(api_key: str, redirect_uri: str) -> tuple[str, str, str]:
    """Build Etsy OAuth authorization URL for web flow.

    Returns (auth_url, state, code_verifier).
    """
    verifier, challenge = _generate_pkce()
    state = secrets.token_urlsafe(16)

    auth_params = urlencode({
        "response_type": "code",
        "client_id": api_key,
        "redirect_uri": redirect_uri,
        "scope": DEFAULT_SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"{ETSY_AUTH_URL}?{auth_params}"
    return auth_url, state, verifier


def exchange_code(api_key: str, code: str, verifier: str,
                  redirect_uri: str) -> EtsyCredentials:
    """Exchange authorization code for tokens (web callback flow)."""
    with httpx.Client() as http:
        resp = http.post(
            ETSY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": api_key,
                "redirect_uri": redirect_uri,
                "code": code,
                "code_verifier": verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        token_data = resp.json()

    access_token = token_data["access_token"]
    refresh_token_val = token_data["refresh_token"]
    user_id = access_token.split(".")[0] if "." in access_token else ""

    creds = EtsyCredentials(
        api_key=api_key,
        access_token=access_token,
        refresh_token=refresh_token_val,
        user_id=user_id,
    )

    shop_id = _get_shop_id(creds)
    if shop_id:
        creds = EtsyCredentials(
            api_key=creds.api_key,
            access_token=creds.access_token,
            refresh_token=creds.refresh_token,
            user_id=creds.user_id,
            shop_id=shop_id,
        )
    return creds


def upload_listing_image_bytes(
    creds: EtsyCredentials,
    listing_id: str,
    image_bytes: bytes,
    filename: str = "preview.png",
    content_type: str = "image/png",
    on_refresh: callable = None,
) -> str:
    """Upload a preview image from bytes. Returns listing_image_id."""
    if not creds.shop_id:
        raise ValueError("No shop_id in credentials.")

    url = f"{ETSY_API_BASE}/shops/{creds.shop_id}/listings/{listing_id}/images"

    logger.info("Uploading preview image bytes: %s (%.0f KB)", filename, len(image_bytes) / 1024)
    with httpx.Client() as http:
        resp = http.request(
            "POST", url, headers=_api_headers(creds),
            files={"image": (filename, image_bytes, content_type)},
        )
        if resp.status_code == 401 and on_refresh:
            creds = refresh_access_token(creds)
            on_refresh(creds)
            resp = http.request(
                "POST", url, headers=_api_headers(creds),
                files={"image": (filename, image_bytes, content_type)},
            )
        resp.raise_for_status()

    result = resp.json()
    return str(result["listing_image_id"])


def upload_listing_file_bytes(
    creds: EtsyCredentials,
    listing_id: str,
    file_bytes: bytes,
    filename: str = "download.png",
    on_refresh: callable = None,
) -> str:
    """Upload a digital download file from bytes. Returns listing_file_id."""
    if not creds.shop_id:
        raise ValueError("No shop_id in credentials.")

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > 20:
        raise ValueError(f"File too large ({size_mb:.1f} MB). Etsy limit is 20 MB per file.")

    url = f"{ETSY_API_BASE}/shops/{creds.shop_id}/listings/{listing_id}/files"

    logger.info("Uploading digital file bytes: %s (%.1f MB)", filename, size_mb)
    with httpx.Client() as http:
        resp = http.request(
            "POST", url, headers=_api_headers(creds),
            files={"file": (filename, file_bytes, "application/octet-stream")},
        )
        if resp.status_code == 401 and on_refresh:
            creds = refresh_access_token(creds)
            on_refresh(creds)
            resp = http.request(
                "POST", url, headers=_api_headers(creds),
                files={"file": (filename, file_bytes, "application/octet-stream")},
            )
        resp.raise_for_status()

    result = resp.json()
    return str(result["listing_file_id"])
