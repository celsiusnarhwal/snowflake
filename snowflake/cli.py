import json

from joserfc.jwk import RSAKey


def keygen():
    key = RSAKey.generate_key(
        2048, parameters={"use": "sig", "alg": "RS256"}, private=True
    )

    print(json.dumps(key.as_dict(private=True)))
