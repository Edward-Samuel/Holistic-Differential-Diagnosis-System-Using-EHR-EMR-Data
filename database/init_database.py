from pymongo import MongoClient
from datetime import datetime, timedelta
import random

def init_database():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['diagnosis_system']
    
    # Clear existing collections
    db.patients.drop()
    db.diagnoses.drop()
    
    # Sample conditions and symptoms
    conditions = [
        "Hypertension", "Type 2 Diabetes", "Asthma", "Migraine",
        "Allergic Rhinitis", "GERD", "Anxiety Disorder"
    ]
    
    symptoms = [
        "Fever", "Cough", "Shortness of Breath", "Fatigue", "Body Ache",
        "Headache", "Loss of Taste", "Sore Throat", "Runny Nose",
        "Nausea", "Dizziness", "Chest Pain", "Abdominal Pain",
        "Joint Pain", "Rash", "Swelling"
    ]
    
    medications = [
        "Lisinopril", "Metformin", "Albuterol", "Sumatriptan",
        "Cetirizine", "Omeprazole", "Sertraline"
    ]
    
    # Create sample patients
    sample_patients = []
    for i in range(1, 21):  # Create 20 sample patients
        patient = {
            "patient_id": f"P{i:03d}",
            "name": f"Patient {i}",
            "age": random.randint(25, 75),
            "gender": random.choice(["Male", "Female"]),
            "previous_conditions": random.sample(conditions, random.randint(0, 3)),
            "current_medications": random.sample(medications, random.randint(0, 2)),
            "allergies": random.sample(medications, random.randint(0, 1)),
            "medical_history": []
        }
        
        # Generate medical history entries
        num_entries = random.randint(3, 8)
        base_date = datetime.now() - timedelta(days=365)
        
        for _ in range(num_entries):
            entry_date = base_date + timedelta(days=random.randint(0, 365))
            entry = {
                "date": entry_date,
                "type": random.choice(["Check-up", "Emergency", "Follow-up"]),
                "symptoms": random.sample(symptoms, random.randint(1, 4)),
                "diagnosis": random.choice(conditions),
                "prescribed_medications": random.sample(medications, random.randint(1, 2)),
                "notes": f"Routine {random.choice(['follow-up', 'check-up', 'examination'])}"
            }
            patient["medical_history"].append(entry)
        
        # Sort medical history by date
        patient["medical_history"].sort(key=lambda x: x["date"])
        sample_patients.append(patient)
    
    # Insert patients into database
    db.patients.insert_many(sample_patients)
    
    # Create sample diagnoses
    sample_diagnoses = []
    for patient in sample_patients:
        num_diagnoses = random.randint(2, 5)
        base_date = datetime.now() - timedelta(days=180)
        
        for _ in range(num_diagnoses):
            primary_symptoms = random.sample(symptoms, random.randint(1, 3))
            secondary_symptoms = random.sample(
                [s for s in symptoms if s not in primary_symptoms],
                random.randint(0, 2)
            )
            
            diagnosis = {
                "patient_id": patient["patient_id"],
                "date": base_date + timedelta(days=random.randint(0, 180)),
                "primary_symptoms": primary_symptoms,
                "secondary_symptoms": secondary_symptoms,
                "diagnoses": random.sample(conditions, random.randint(1, 3)),
                "confidence_scores": [
                    round(random.uniform(0.4, 0.9), 2)
                    for _ in range(random.randint(1, 3))
                ],
                "recommended_tests": [
                    "Blood Test",
                    "X-Ray",
                    "ECG"
                ][:random.randint(1, 3)],
                "notes": "Generated diagnosis record"
            }
            sample_diagnoses.append(diagnosis)
    
    # Insert diagnoses into database
    db.diagnoses.insert_many(sample_diagnoses)
    
    # Create indexes for better query performance
    db.patients.create_index("patient_id", unique=True)
    db.diagnoses.create_index("patient_id")
    db.diagnoses.create_index([("date", -1)])
    
    print(f"Database initialized with:")
    print(f"- {len(sample_patients)} patients")
    print(f"- {len(sample_diagnoses)} diagnosis records")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    init_database()
