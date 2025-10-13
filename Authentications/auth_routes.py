from fastapi import APIRouter, Depends, HTTPException
from database.db import get_firestore_db
from Authentications.utils import create_access_token, hash_password, verify_api_key, verify_password
from model.model import LoginUser, UserCreate, ResetPasswordRequest
from datetime import datetime


Auth_router = APIRouter()


def _snapshot_get(snapshot_or_dict, field, default=None):
    """Safely extract field from a DocumentSnapshot or dict.

    If a DocumentSnapshot is provided, call .to_dict() and ensure the result
    is a dict before returning the requested field. This prevents calling
    .get on Firestore Timestamp objects (DatetimeWithNanoseconds).
    """
    if snapshot_or_dict is None:
        return default
    # If it's a DocumentSnapshot-like object
    try:
        if hasattr(snapshot_or_dict, "to_dict"):
            data = snapshot_or_dict.to_dict()
        else:
            data = snapshot_or_dict
    except Exception:
        data = snapshot_or_dict
    if isinstance(data, dict):
        return data.get(field, default)
    return default


def _normalize_value(v):
    # convert Firestore timestamp-like objects to ISO strings, keep datetimes as ISO
    try:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        # common Firestore Timestamp objects have 'to_datetime' or 'to_rfc3339' methods
        if hasattr(v, 'to_datetime') and callable(v.to_datetime):
            return v.to_datetime().isoformat()
        if hasattr(v, 'to_rfc3339') and callable(v.to_rfc3339):
            try:
                return v.to_rfc3339()
            except Exception:
                pass
        # fallback for objects with seconds/nanos
        if hasattr(v, 'seconds') and hasattr(v, 'nanos'):
            try:
                ts = float(v.seconds) + float(v.nanos) / 1e9
                return datetime.fromtimestamp(ts).isoformat()
            except Exception:
                pass
        # otherwise return as-is (will be JSON serialized by FastAPI if possible)
        return v
    except Exception:
        return str(v)


def normalize_doc(snapshot_or_dict):
    """Return a plain dict from a DocumentSnapshot or dict, converting
    Timestamp-like fields to ISO strings.
    """
    if snapshot_or_dict is None:
        return {}
    try:
        if hasattr(snapshot_or_dict, 'to_dict'):
            data = snapshot_or_dict.to_dict() or {}
        elif isinstance(snapshot_or_dict, dict):
            data = snapshot_or_dict
        else:
            # unexpected type, try to cast to dict
            data = dict(snapshot_or_dict)
    except Exception:
        # can't convert to dict, return empty
        return {}

    out = {}
    for k, val in data.items():
        out[k] = _normalize_value(val)
    # preserve id if present on snapshot
    try:
        if hasattr(snapshot_or_dict, 'id') and snapshot_or_dict.id:
            out['id'] = snapshot_or_dict.id
    except Exception:
        pass
    return out

@Auth_router.post("/register")
def create_user(user: UserCreate, db=Depends(get_firestore_db)):
    try:
        users_collection = db.collection("signup")

        # check if email already exists
        existing = list(users_collection.where("email", "==", user.email).stream())
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user_hash_password = hash_password(user.password)
        user_doc = {
            "name": user.name,
            "email": user.email,
            "password": user_hash_password,
        }
    # create a new document and set the data explicitly so doc_ref is a DocumentReference
        doc_ref = users_collection.document()
        doc_ref.set(user_doc)
        created = doc_ref.get()
        created_data = normalize_doc(created) if created.exists else normalize_doc(user_doc)

        # Use normalized dict values (already converted) to avoid Timestamp misuse
        email_val = created_data.get("email")
        name_val = created_data.get("name")

        token = create_access_token(
            data={"email": email_val, "name": name_val, "user_id": doc_ref.id}
        )

        return {"data": {"name": name_val, "email": email_val, "token": token},
                "message": "User registered and login successfully",
                "status": "success"}
    except Exception as e:
        import traceback
        # collect some helpful variable type info for debugging
        debug_vars = {}
        try:
            debug_vars['created_type'] = type(created).__name__
        except Exception:
            debug_vars['created_type'] = None
        try:
            debug_vars['created_data_type'] = type(created_data).__name__
        except Exception:
            debug_vars['created_data_type'] = None
        return {"message": str(e), "status": "error", "data": None, "trace": traceback.format_exc(), "debug": debug_vars}


@Auth_router.post("/login", dependencies=[Depends(verify_api_key)])
def login_user(user: LoginUser, db=Depends(get_firestore_db)):
    try:
        users_collection = db.collection("signup")

        matches = list(users_collection.where("email", "==", user.email).stream())
        if not matches:
            raise HTTPException(status_code=404, detail="Email not found")

        doc = matches[0]
        db_user = normalize_doc(doc)
        stored_hash = db_user.get("password")
        if not stored_hash:
            raise HTTPException(status_code=401, detail="User has no password set")

        is_valid_password = verify_password(user.password, stored_hash)
        if not is_valid_password:
            raise HTTPException(status_code=401, detail="Invalid password")

        # use normalized doc values for token and response
        token = create_access_token(
            data={"email": db_user.get("email"), "name": db_user.get("name"), "user_id": doc.id}
        )

        return {"data": {"name": db_user.get("name"), "email": db_user.get("email"), "token": token},
                "message": "User logged in successfully",
                "status": "success"}
    except Exception as e:
        import traceback
        debug_vars = {}
        try:
            debug_vars['doc_type'] = type(doc).__name__
        except Exception:
            debug_vars['doc_type'] = None
        try:
            debug_vars['db_user_type'] = type(db_user).__name__
        except Exception:
            debug_vars['db_user_type'] = None
        try:
            debug_vars['stored_hash_type'] = type(stored_hash).__name__
        except Exception:
            debug_vars['stored_hash_type'] = None
        return {"message": str(e), "status": "error", "data": None, "trace": traceback.format_exc(), "debug": debug_vars}

@Auth_router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db=Depends(get_firestore_db)):
    users_collection = db.collection("signup")

    # normalize email to lowercase & strip spaces
    email = request.email.strip().lower()

    matches = list(users_collection.where("email", "==", email).stream())
    if not matches:
        # debug: list existing emails
        # Defensive: convert each snapshot to dict and guard .get()
        all_users = []
        for d in users_collection.stream():
            all_users.append(normalize_doc(d).get("email"))
        raise HTTPException(
            status_code=404,
            detail=f"Email not found. Provided={email}, Existing={all_users}"
        )

    doc = matches[0]

    hashed_pw = hash_password(request.new_password)
    users_collection.document(doc.id).update({"password": hashed_pw})

    return {
        "message": f"Password has been reset for {email}",
        "status": "success"
    }
