from fastapi import Depends,HTTPException
from fastapi.security import OAuth2PasswordBearer,APIKeyHeader
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import jwt
import os


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
API_KEY_NAME = "x-api-key"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Use PBKDF2-SHA256 to avoid bcrypt and its 72-byte input limitation.
# PBKDF2-SHA256 is a secure, widely-supported KDF and does not impose a 72-byte limit.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_BCRYPT_MAX_BYTES = 72


def _truncate_to_bcrypt_bytes(s: str) -> str:
    """Truncate the input string so its UTF-8 encoding is at most 72 bytes.

    bcrypt operates on the raw bytes and has a 72-byte limit. Truncating by
    bytes (not characters) preserves consistent behavior across hashing and
    verification.
    """
    if s is None:
        return s
    b = s.encode("utf-8")
    if len(b) <= _BCRYPT_MAX_BYTES:
        return s
    # truncate bytes and decode back ignoring partial multibyte characters
    truncated = b[:_BCRYPT_MAX_BYTES]
    return truncated.decode("utf-8", errors="ignore")


def verify_password(plain_password, hashed_password):
    """Safely verify a plaintext password against a stored hash.

    Plaintext is truncated to 72 bytes (bcrypt limit) before verification.
    Returns False if the stored hash is missing or verification fails.
    """
    if not hashed_password:
        # No hash stored for this user
        print("❌ verify_password: missing hashed_password")
        return False
    try:
        # Non-sensitive runtime log: show byte-length before truncation and after
        if plain_password is None:
            print("verify_password: received None plaintext")
        else:
            b_len = len(plain_password.encode("utf-8"))
            safe_plain = _truncate_to_bcrypt_bytes(plain_password)
            safe_len = len(safe_plain.encode("utf-8")) if safe_plain is not None else 0
            print(f"verify_password: plaintext_bytes={b_len}, used_bytes={safe_len}")
        return pwd_context.verify(safe_plain, hashed_password)
    except Exception as e:
        # Passlib may raise ValueError for malformed hashes; swallow and return False
        print("❌ verify_password error:", e)
        return False

def hash_password(password):
    if not password:
        raise ValueError("Password must be provided")
    # Non-sensitive runtime log: show byte-length and truncation info
    b_len = len(password.encode("utf-8"))
    safe_pw = _truncate_to_bcrypt_bytes(password)
    safe_len = len(safe_pw.encode("utf-8")) if safe_pw is not None else 0
    print(f"hash_password: plaintext_bytes={b_len}, used_bytes={safe_len}")
    return pwd_context.hash(safe_pw)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    try: 
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode,  SECRET_KEY , algorithm=ALGORITHM) # type: ignore
    except Exception as e:
        print('An exception occurred')
        print(e)
        return None

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # type: ignore
        return payload
    except jwt.ExpiredSignatureError:
        print('Token expired')
        return None
    except jwt.InvalidTokenError:
        print('Invalid token')
        return None
    except Exception as e:
        print('An exception occurred')
        print(e)
        return None    

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # type: ignore
        if decoded_token:
            return decoded_token
        else:
            return HTTPException(status_code=401, detail="Token not parseable")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print('An exception occurred')
        print(e)
        return HTTPException(status_code=401, detail="Invalid token")
    

def verify_api_key(api_key_header: str = Depends(api_key_header)):
    try:
        # query api keys table to check if api key exists and is active, and userid match the one in the token
        # db_api_key = get_api_key(userId)
        if api_key_header == os.getenv("API_KEY"):
            return api_key_header
        else:
            raise HTTPException(status_code=401, detail="Invalid API Key")
    except Exception as e:
      print('An exception occurred',e)
      raise HTTPException(status_code=401, detail="Invalid API Key")
    