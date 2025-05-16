import json
import time
import uuid
from pathlib import Path

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from authlib.jose import JsonWebKey, RSAKey, jwt
from authlib.oidc.core import IDToken

from snowflake.settings import settings

oauth = OAuth()

PRIVATE_KEY_FILE = Path(__file__).parent / "data" / "private_key.json"


def get_oauth_client(**kwargs) -> StarletteOAuth2App:
    return oauth.register(
        name=uuid.uuid4().hex,
        authorize_url="https://discord.com/oauth2/authorize",
        access_token_url="https://discord.com/api/oauth2/token",
        api_base_url="https://discord.com/api/",
        **kwargs,
    )


def create_private_key() -> RSAKey:
    key: RSAKey = JsonWebKey.generate_key(kty="RSA", crv_or_size=2048, is_private=True)

    PRIVATE_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_KEY_FILE.write_text(key.as_json(is_private=True))

    return key


def get_private_key() -> RSAKey:
    if PRIVATE_KEY_FILE.exists():
        return JsonWebKey.import_key(json.load(PRIVATE_KEY_FILE.open()))

    return create_private_key()


def create_id_token(client_id: str, user_info: dict):
    now = int(time.time())

    claims = {
        "iss": settings().public_url,
        "sub": user_info["id"],
        "aud": client_id,
        "iat": now,
        "exp": now + settings().token_lifetime,
        "preferred_username": user_info["username"],
        "name": user_info["global_name"],
        "locale": user_info["locale"],
        "picture": f"https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}."
        f"{'gif' if user_info['avatar'].startswith('a_') else 'png'}",
    }

    if email := user_info.get("email"):
        claims.update({"email": email, "email_verified": user_info["verified"]})

    return jwt.encode({"alg": "RS256"}, claims, get_private_key()).decode()


def get_jwks():
    return {"keys": [get_private_key().as_dict()]}


async def decode_jwt(token: str):
    decoded = jwt.decode(
        token,
        get_jwks(),
        claims_cls=IDToken,
        claims_options={"iss": {"value": settings().public_url}},
    )
    decoded.validate()

    return decoded
