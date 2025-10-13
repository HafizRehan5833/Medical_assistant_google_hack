import os
import firebase_admin
from firebase_admin import credentials, firestore

# ✅ Absolute or relative path to your service account JSON
FIREBASE_KEY_PATH = os.path.join(
    os.path.dirname(__file__), "google_hack.json"
)

_db_client = None  # cache Firestore client to avoid re-initialization


def get_firestore_db():
    """Return a Firestore client, initializing Firebase if needed."""
    global _db_client

    try:
        if _db_client is not None:
            return _db_client  # return cached client if already initialized

        # If Firebase is already initialized, skip re-initialization
        if not firebase_admin._apps:
            if not os.path.exists(FIREBASE_KEY_PATH):
                raise FileNotFoundError(f"Firebase key not found: {FIREBASE_KEY_PATH}")

            cred = credentials.Certificate(FIREBASE_KEY_PATH)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized successfully.")

        _db_client = firestore.client()
        return _db_client

    except Exception as e:
        print(f"❌ Error initializing Firestore: {e}")
        raise RuntimeError(f"Failed to connect to Firestore: {e}")
