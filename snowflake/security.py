import json
import time
from pathlib import Path

from joserfc import jwt
from joserfc.jwk import RSAKey

from snowflake.settings import settings

PRIVATE_KEY_FILE = Path(__file__).parent / "data" / "keys" / "private_key.json"


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


async def create_tokens(*, issuer: str, client_id: str, nonce: str, user_info: dict):
    now = int(time.time())
    expiry = now + settings().token_lifetime

    access_claims = {
        "iss": issuer,
        "sub": user_info["id"],
        "aud": client_id,
        "iat": now,
        "exp": expiry,
        "nonce": nonce,
    }

    identity_claims = {
        **access_claims,
        "preferred_username": user_info["username"],
        "name": user_info["global_name"],
        "locale": user_info["locale"],
        "picture": f"https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}."
        f"{'gif' if user_info['avatar'].startswith('a_') else 'png'}",
    }

    if email := user_info.get("email"):
        identity_claims.update(
            {"email": email, "email_verified": user_info["verified"]}
        )

    access_token = create_jwt(access_claims, get_private_key())
    id_token = create_jwt(identity_claims, get_private_key())

    async with settings().redis as redis:
        await redis.set(access_token, json.dumps(identity_claims), exat=expiry)

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_at": expiry,
        "id_token": id_token,
    }


def get_jwks():
    return {"keys": [get_private_key().as_dict(private=False)]}
