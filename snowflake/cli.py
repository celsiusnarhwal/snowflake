import base64
import secrets
import sys
import typing as t

from pydantic import Field, TypeAdapter, ValidationError

def secret():
    if len(sys.argv) >= 2:
        try:
            TypeAdapter(t.Annotated[int, Field(ge=32)]).validate_python(sys.argv[1])
        except ValidationError:
            print(
                f"The secret length must be an integer greater than or equal to 32. (recieved: {sys.argv[1]})",
                file=sys.stderr,
            )
            exit(1)

    print(base64.b64encode(secrets.token_bytes()).decode())
