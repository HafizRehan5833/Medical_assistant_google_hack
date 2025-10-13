from agents import function_tool
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv
import os

# ===== Environment Setup =====
load_dotenv()

# ===== Firebase Initialization =====
cred = credentials.Certificate("google_hack.json")  # 🔹 Make sure file path is correct
initialize_app(cred)

db = firestore.client()
collection = db.collection("Medicines_info")


# ===== READ ALL MEDICINES =====
@function_tool
def read_medicines():
    print("Fetching all medicines from Firestore")
    """
    Fetch all medicines from Firestore.
    """
    try:
        docs = collection.stream()
        medicines_list = [{**doc.to_dict(), "id": doc.id} for doc in docs]
        return {
            "Data": medicines_list,
            "Error": False,
            "Message": "All medicines fetched successfully."
        }
    except Exception as e:
        return {"Data": [], "Error": True, "Message": f"Error fetching medicines: {str(e)}"}


# ===== READ MEDICINE BY NAME =====
@function_tool
def read_medicine_by_name(name: str):
    print("Fetching medicine by name:", name)
    """
    Fetch a medicine document by its 'Medicine Name' field (case-insensitive).
    """
    try:
        name = name.strip().lower()
        docs = collection.stream()
        for doc in docs:
            data = doc.to_dict()
            if data.get("Medicine Name", "").strip().lower() == name:
                data["id"] = doc.id
                return {
                    "Data": data,
                    "Error": False,
                    "Message": "Medicine fetched successfully."
                }

        # If not found
        return {
            "Data": {},
            "Error": True,
            "Message": f"Medicine '{name}' not found in database."
        }

    except Exception as e:
        return {"Data": {}, "Error": True, "Message": f"Error fetching medicine: {str(e)}"}
