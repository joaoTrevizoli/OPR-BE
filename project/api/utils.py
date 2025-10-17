from passlib.context import CryptContext
from hashlib import sha256

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    if isinstance(password, str):
        pw_bytes = password.encode("utf-8")
    else:
        pw_bytes = password
    if len(pw_bytes) > 72:
        password = sha256(pw_bytes).hexdigest()
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if isinstance(plain, str):
        pw_bytes = plain.encode("utf-8")
    else:
        pw_bytes = plain
    if len(pw_bytes) > 72:
        plain = sha256(pw_bytes).hexdigest()
    return pwd_context.verify(plain, hashed)
