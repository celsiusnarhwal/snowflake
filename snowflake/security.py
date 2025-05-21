import json
import time
from pathlib import Path

from authlib.integrations.starlette_client import StarletteOAuth2App
from fastapi import Request
from joserfc import jwt
from joserfc.jwk import KeySet, RSAKey

from snowflake.settings import settings
from snowflake.types import SnowflakeAuthorizationData

PRIVATE_KEY_FILE = Path(__file__).parent / "data" / "keys" / "jwt_private_key.json"


def create_private_key():
    key = RSAKey.generate_key(2048, private=True, auto_kid=True)
    PRIVATE_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(key.as_dict(private=True), PRIVATE_KEY_FILE.open("w"))


def get_private_key() -> RSAKey:
    if PRIVATE_KEY_FILE.exists():
        try:
            return RSAKey.import_key(json.load(PRIVATE_KEY_FILE.open()))
        except ValueError:
            pass

    create_private_key()

    return get_private_key()


def create_jwt(claims, key):
    return jwt.encode({"alg": "RS256"}, claims, key)


def decode_jwt(token: str, key, **claims):
    decoded = jwt.decode(token, key)
    jwt.JWTClaimsRegistry(**claims).validate(decoded.claims)

    return decoded


async def create_tokens(
    *,
    request: Request,
    discord: StarletteOAuth2App,
    authorization_data: SnowflakeAuthorizationData,
    discord_token: dict,
):
    user_resp = await discord.get("users/@me", token=discord_token)
    user_resp.raise_for_status()
    user_info = user_resp.json()

    now = int(time.time())
    expiry = now + settings().token_lifetime

    access_claims = {
        "iss": str(request.base_url),
        "sub": user_info["id"],
        "aud": str(request.url_for("userinfo")),
        "iat": now,
        "exp": expiry,
        "preferred_username": user_info["username"],
        "name": user_info["global_name"],
        "locale": user_info["locale"],
        "picture": f"https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}."
        f"{'gif' if user_info['avatar'].startswith('a_') else 'png'}",
    }

    if "email" in authorization_data.scopes:
        access_claims.update(
            {
                "email": user_info.get("email"),
                "email_verified": user_info.get("verified"),
            }
        )

    identity_claims = {
        **access_claims,
        "aud": discord.client_id,
        "nonce": authorization_data.nonce,
    }

    access_token = create_jwt(access_claims, get_private_key())
    id_token = create_jwt(identity_claims, get_private_key())

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_at": expiry,
        "id_token": id_token,
    }


def get_jwks():
    return KeySet([get_private_key()]).as_dict(private=False)
