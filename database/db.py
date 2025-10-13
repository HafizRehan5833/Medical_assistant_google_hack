
import firebase_admin
from firebase_admin import credentials, firestore

import os
firebase_json_path = os.path.join(os.path.dirname(__file__), 'google_hack.json')

def get_firestore_db():
    """Return a Firestore client, initializing Firebase if needed."""
 
    try:
            print("Initializing Firebase with provided credentials...")
            cred = credentials.Certificate(firebase_json_path)
            firebase_admin.initialize_app(cred, {"database_url": os.getenv("db_url")})
            firebase_initialized = True
            db = firestore.client()
            return db
            print("Firebase initialized successfully.")
    except Exception as e:
            print('Warning: Firebase not initialized automatically:', e)
            db = None
    
