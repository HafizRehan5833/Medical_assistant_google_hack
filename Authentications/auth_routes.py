from fastapi import APIRouter, Depends, HTTPException
from database.db import get_firestore_db
from Authentications.utils import create_access_token, hash_password,  verify_password
from model.model import LoginUser, UserCreate, ResetPasswordRequest
from datetime import datetime
from google.cloud.firestore import Client

Auth_router = APIRouter()

# ================== Utility Functions ==================

def _normalize_value(v):
    """Convert Firestore timestamp-like objects to ISO strings."""
    try:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        if hasattr(v, "to_datetime") and callable(v.to_datetime):
            return v.to_datetime().isoformat()
        if hasattr(v, "seconds") and hasattr(v, "nanos"):
            ts = float(v.seconds) + float(v.nanos) / 1e9
            return datetime.fromtimestamp(ts).isoformat()
        return v
    except Exception:
        return str(v)


def normalize_doc(snapshot_or_dict):
    """Safely convert Firestore document to plain dict."""
    if snapshot_or_dict is None:
        return {}
    try:
        data = snapshot_or_dict.to_dict() if hasattr(snapshot_or_dict, "to_dict") else dict(snapshot_or_dict)
    except Exception:
        return {}

    normalized = {k: _normalize_value(v) for k, v in data.items()}
    if hasattr(snapshot_or_dict, "id"):
        normalized["id"] = getattr(snapshot_or_dict, "id", None)
    return normalized

# ================== Auth Routes ==================

@Auth_router.post("/register")
def create_user(user: UserCreate, db: Client = Depends(get_firestore_db)):
    try:
        users_collection = db.collection("signup")

        # Normalize email
        email = user.email.strip().lower()

        # Check if user already exists
        existing = list(users_collection.where("email", "==", email).stream())
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password and create user
        hashed_pw = hash_password(user.password)
        user_doc = {"name": user.name, "email": email, "password": hashed_pw}

        doc_ref = users_collection.document()
        doc_ref.set(user_doc)
        created = doc_ref.get()
        created_data = normalize_doc(created)

        token = create_access_token(
            data={"email": created_data.get("email"), "name": created_data.get("name"), "user_id": doc_ref.id}
        )

        return {
            "data": {"name": created_data.get("name"), "email": created_data.get("email"), "token": token},
            "message": "User registered and logged in successfully",
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}")


@Auth_router.post("/login")
def login_user(user: LoginUser, db: Client = Depends(get_firestore_db)):
    try:
        users_collection = db.collection("signup")

        email = user.email.strip().lower()
        matches = list(users_collection.where("email", "==", email).stream())

        if not matches:
            raise HTTPException(status_code=404, detail="Email not found")

        doc = matches[0]
        db_user = normalize_doc(doc)
        stored_hash = db_user.get("password")

        if not stored_hash or not verify_password(user.password, stored_hash):
            raise HTTPException(status_code=401, detail="Invalid password")

        token = create_access_token(
            data={"email": db_user.get("email"), "name": db_user.get("name"), "user_id": doc.id}
        )

        return {
            "data": {"name": db_user.get("name"), "email": db_user.get("email"), "token": token},
            "message": "User logged in successfully",
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {e}")


@Auth_router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Client = Depends(get_firestore_db)):
    try:
        users_collection = db.collection("signup")
        email = request.email.strip().lower()

        matches = list(users_collection.where("email", "==", email).stream())
        if not matches:
            all_users = [normalize_doc(d).get("email") for d in users_collection.stream()]
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Password reset failed: {e}")
