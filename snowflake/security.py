import time
from functools import lru_cache

# noinspection PyUnresolvedReferences
from authlib.integrations.starlette_client import StarletteOAuth2App
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from joserfc import jwt
from joserfc.jwk import ECKey, KeySet
from joserfc.jwt import Token

from snowflake import utils
from snowflake.serializable import SnowflakeRefreshToken
from snowflake.settings import settings


@lru_cache(maxsize=settings().key_history + 3)
def derive_private_key(secret: bytes, version: int) -> ECKey:
    """
    Derive a private key from a secret.

    Parameters
    ----------
    secret: str
        The secret from which to derive the key.

    version: int
        The key version.

    Returns
    -------
    ECKey
        The derived key.
    """
    hkdf_key = HKDF(
        algorithm=hashes.SHA256(),
        length=40,
        salt=None,
        info=f"snowflake/{settings().rotation_interval}s/v{version}/es256".encode(),
    ).derive(secret)

    curve = ec.SECP256R1()
    derived_key = ec.derive_private_key(
        int.from_bytes(hkdf_key) % (curve.group_order - 1) + 1, curve
    )

    return ECKey.import_key(derived_key, {"alg": "ES256", "use": "sig"})


def get_private_key_set(*, include_unused: bool = False) -> KeySet:
    """
    Get the private key set.

    Parameters
    ----------
    include_unused: bool, default=False
        Whether to include key versions not used for signing.
    """
    secret = settings().secret.get_secret_value()
    current_version = int(time.time()) // settings().rotation_interval

    if include_unused:
        versions = [current_version + 1] + [
            current_version - i for i in range(settings().key_history + 1)
        ]
    else:
        versions = [current_version]

    return KeySet([derive_private_key(secret, version) for version in versions])


def create_jwt(claims: dict) -> str:
    """
    Create a JWT.
    """
    return jwt.encode({"alg": "ES256"}, claims, get_private_key_set())


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
        get_private_key_set(include_unused=True).as_dict(private=False),
        parameters={"use": "sig"},
    )


async def create_tokens(
    *,
    discord: StarletteOAuth2App,
    discord_token: dict,
    oidc_metadata: dict,
    groups: list[str],
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

    if "profile" in scopes:
        access_claims["name"] = access_claims["nickname"]

    if "groups" in scopes:
        guilds = (
            (await discord.get("users/@me/guilds", token=discord_token))
            .raise_for_status()
            .json()
        )

        access_claims["groups"] = [guild["id"] for guild in guilds if guild["id"] in groups or not groups]

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
        tokens["refresh_token"] = SnowflakeRefreshToken(token=discord_token["refresh_token"], groups=groups).to_jwt()

    return tokens
