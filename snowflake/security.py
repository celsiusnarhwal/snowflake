import json
import time
from json import JSONDecodeError
from pathlib import Path

# noinspection PyUnresolvedReferences
from authlib.integrations.starlette_client import StarletteOAuth2App
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet
from joserfc.jwt import Token

from snowflake import utils
from snowflake.settings import settings

PRIVATE_KEY_FILE = Path(__file__).parent / "data" / "keys" / "jwt_private_key.json"


def create_private_key() -> None:
    """
    Create a new private key.
    """
    key = KeySet.generate_key_set(
        "RSA", 2048, parameters={"use": "sig"}, private=True, count=1
    )
    PRIVATE_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(key.as_dict(private=True), PRIVATE_KEY_FILE.open("w"))


def get_private_key() -> KeySet:
    """
    Get the private key, creating one if necessary.
    """
    if settings().private_key:
        return settings().private_key

    try:
        return KeySet.import_key_set(json.load(PRIVATE_KEY_FILE.open()))
    except (FileNotFoundError, JSONDecodeError, JoseError):
        pass

    create_private_key()

    return get_private_key()


def create_jwt(claims: dict) -> str:
    """
    Create a JWT.
    """
    return jwt.encode({"alg": "RS256"}, claims, get_private_key())


def decode_jwt(token: str, **claims: dict) -> Token:
    """
    Decode a JWT.
    """
    decoded = jwt.decode(token, get_jwks())
    jwt.JWTClaimsRegistry(**claims).validate(decoded.claims)

    return decoded


def get_jwks() -> KeySet:
    """
    Get the public JSON Web Key Set.
    """
    return KeySet.import_key_set(
        get_private_key().as_dict(private=False), parameters={"use": "sig"}
    )


async def create_tokens(
    *,
    discord: StarletteOAuth2App,
    discord_token: dict,
    oidc_metadata: dict,
    nonce: str | None = None,
    include_refresh_token: bool = True,
) -> dict[str, str | int]:
    """
    Create a pair of access and ID tokens.
    """
    access_claims = await discord.userinfo(token=discord_token)

    now = int(time.time())
    expiry = now + settings().token_lifetime

    access_claims.update(
        {
            "iss": oidc_metadata["issuer"],
            "aud": oidc_metadata["userinfo_endpoint"],
            "iat": now,
            "exp": expiry,
        }
    )

    scopes = utils.convert_scopes(
        discord_token["scope"], to_format="openid", output_type=list
    )

    if "groups" in scopes:
        guilds = (
            (await discord.get("users/@me/guilds", token=discord_token))
            .raise_for_status()
            .json()
        )

        access_claims["groups"] = [guild["id"] for guild in guilds]

    identity_claims = {
        **access_claims,
        "aud": discord.client_id,
    }

    if nonce is not None:
        identity_claims["nonce"] = nonce

    access_token = create_jwt(access_claims)
    identity_token = create_jwt(identity_claims)

    tokens = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_at": expiry,
        "id_token": identity_token,
    }

    if include_refresh_token:
        tokens["refresh_token"] = discord_token["refresh_token"]

    return tokens
