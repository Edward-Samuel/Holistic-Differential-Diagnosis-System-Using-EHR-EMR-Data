from pymongo import MongoClient
from typing import Dict, List, Optional
from bson import ObjectId
import json
from datetime import datetime

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

class MongoDB:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['diagnosis_system']
        
    def get_patient_history(self, patient_id: str) -> Dict:
        """Retrieve patient history from the database."""
        # Query to find patient by ID and explicitly include previous_conditions
        patient = self.db.patients.find_one(
            {"patient_id": patient_id},
            {
                "patient_id": 1,
                "previous_conditions": 1,
                "current_medications": 1,
                "allergies": 1,
                "medical_history": 1
            }
        )
        
        if not patient:
            return {"error": "Patient not found"}
            
        # Convert ObjectId to string
        patient['_id'] = str(patient['_id'])
        
        # Ensure previous_conditions exists
        if 'previous_conditions' not in patient:
            patient['previous_conditions'] = []
            
        # Convert ObjectId and dates in medical history
        if 'medical_history' in patient:
            for entry in patient['medical_history']:
                if '_id' in entry:
                    entry['_id'] = str(entry['_id'])
                if 'date' in entry:
                    entry['date'] = entry['date'].isoformat() if isinstance(entry['date'], datetime) else entry['date']
        
        return patient

    def save_diagnosis(self, patient_id: str, diagnosis_data: Dict) -> bool:
        """Save a new diagnosis record."""
        try:
            diagnosis_data["patient_id"] = patient_id
            self.db.diagnoses.insert_one(diagnosis_data)
            return True
        except Exception as e:
            print(f"Error saving diagnosis: {e}")
            return False

    def update_patient_history(self, patient_id: str, new_data: Dict) -> bool:
        """Update patient history with new information."""
        try:
            self.db.patients.update_one(
                {"patient_id": patient_id},
                {"$set": new_data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error updating patient history: {e}")
            return False

    def get_patient_diagnoses(self, patient_id: str) -> List[Dict]:
        """Retrieve all diagnoses for a patient."""
        diagnoses = list(self.db.diagnoses.find(
            {"patient_id": patient_id},
            {"_id": 0}
        ))
        for diagnosis in diagnoses:
            if '_id' in diagnosis:
                diagnosis['_id'] = str(diagnosis['_id'])
            for key, value in diagnosis.items():
                if isinstance(value, datetime):
                    diagnosis[key] = value.isoformat()
        return diagnoses

    def search_similar_cases(self, symptoms: List[str]) -> List[Dict]:
        """Search for similar cases based on symptoms."""
        cases = list(self.db.diagnoses.find(
            {"symptoms": {"$in": symptoms}},
            {"_id": 0}
        ).limit(5))
        for case in cases:
            if '_id' in case:
                case['_id'] = str(case['_id'])
            for key, value in case.items():
                if isinstance(value, datetime):
                    case[key] = value.isoformat()
        return cases

    def close(self):
        """Close the MongoDB connection."""
        self.client.close()
