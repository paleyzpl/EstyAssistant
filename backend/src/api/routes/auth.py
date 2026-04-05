import os

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.credentials import (
    delete_credentials,
    load_credentials,
    load_oauth_state,
    save_credentials,
    save_oauth_state,
)
from etsy_assistant.etsy_api import build_auth_url, exchange_code

router = APIRouter(prefix="/auth/etsy")

ETSY_API_KEY = os.environ.get("ETSY_API_KEY", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


class AuthStartResponse(BaseModel):
    auth_url: str


class AuthStatusResponse(BaseModel):
    connected: bool
    shop_id: str | None = None


class AuthCallbackResponse(BaseModel):
    success: bool
    shop_id: str | None = None


@router.get("/start", response_model=AuthStartResponse)
def start_auth(
    redirect_uri: str = Query(default=""),
):
    """Begin Etsy OAuth flow. Returns URL to redirect the user to."""
    if not ETSY_API_KEY:
        raise HTTPException(status_code=500, detail="ETSY_API_KEY not configured")

    callback_uri = redirect_uri or f"{FRONTEND_URL}/auth/etsy/callback"
    auth_url, state, verifier = build_auth_url(ETSY_API_KEY, callback_uri)

    # Store PKCE state for callback verification
    save_oauth_state(state, verifier, callback_uri)

    return AuthStartResponse(auth_url=auth_url)


@router.post("/callback", response_model=AuthCallbackResponse)
def handle_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    """Exchange OAuth code for tokens. Called after Etsy redirects back."""
    if not ETSY_API_KEY:
        raise HTTPException(status_code=500, detail="ETSY_API_KEY not configured")

    # Verify state and get PKCE verifier
    oauth_state = load_oauth_state(state)
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        creds = exchange_code(
            ETSY_API_KEY, code, oauth_state["verifier"], oauth_state["redirect_uri"]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {e}") from e

    # Save to DynamoDB
    save_credentials(
        api_key=creds.api_key,
        access_token=creds.access_token,
        refresh_token=creds.refresh_token,
        user_id=creds.user_id,
        shop_id=creds.shop_id,
    )

    return AuthCallbackResponse(success=True, shop_id=creds.shop_id)


@router.get("/status", response_model=AuthStatusResponse)
def auth_status():
    """Check if Etsy is connected."""
    creds = load_credentials()
    if not creds:
        return AuthStatusResponse(connected=False)
    return AuthStatusResponse(connected=True, shop_id=creds.get("shop_id"))


@router.post("/disconnect")
def disconnect():
    """Disconnect Etsy account (delete credentials)."""
    delete_credentials()
    return {"success": True}
