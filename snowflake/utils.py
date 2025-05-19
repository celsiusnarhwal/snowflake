import json
import time
import uuid
from pathlib import Path

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from authlib.jose import JsonWebKey, RSAKey, jwt

from snowflake.settings import settings

PRIVATE_KEY_FILE = Path(__file__).parent / "data" / "keys" / "private_key.json"


def get_oauth_client(**kwargs) -> StarletteOAuth2App:
    oauth = OAuth()

    return oauth.register(
        name=uuid.uuid4().hex,
        authorize_url="https://discord.com/oauth2/authorize",
        access_token_url="https://discord.com/api/oauth2/token",
        api_base_url="https://discord.com/api/",
        **kwargs,
    )


def create_private_key():
    key: RSAKey = JsonWebKey.generate_key(kty="RSA", crv_or_size=2048, is_private=True)

    PRIVATE_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_KEY_FILE.write_text(key.as_json(is_private=True))


def get_private_key() -> RSAKey:
    if PRIVATE_KEY_FILE.exists():
        try:
            return JsonWebKey.import_key(json.load(PRIVATE_KEY_FILE.open()))
        except ValueError:
            pass

    create_private_key()

    return get_private_key()


def create_jwt(claims):
    return jwt.encode({"alg": "RS256"}, claims, get_private_key()).decode()


def create_id_token(*, issuer: str, client_id: str, nonce: str, user_info: dict):
    now = int(time.time())

    claims = {
        "iss": issuer,
        "sub": user_info["id"],
        "aud": client_id,
        "iat": now,
        "exp": now + settings().token_lifetime,
        "nonce": nonce,
        "preferred_username": user_info["username"],
        "name": user_info["global_name"],
        "locale": user_info["locale"],
        "picture": f"https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}."
        f"{'gif' if user_info['avatar'].startswith('a_') else 'png'}",
    }

    if email := user_info.get("email"):
        claims.update({"email": email, "email_verified": user_info["verified"]})

    id_token = jwt.encode({"alg": "RS256"}, claims, get_private_key()).decode()

    return {"id_token": id_token}


def get_jwks():
    return {"keys": [get_private_key().as_dict()]}
