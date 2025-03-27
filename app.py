from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import pymongo
from models.diagnosis import DiagnosisModel
from database.mongodb import MongoDB
from utils.symptom_analyzer import SymptomAnalyzer

# Define response models
class PatientHistory(BaseModel):
    patient_id: str
    previous_conditions: List[str] = []
    current_medications: List[str] = []
    allergies: List[str] = []
    medical_history: List[dict] = []

class SymptomInput(BaseModel):
    primary_symptoms: List[str]
    secondary_symptoms: Optional[List[str]] = []
    patient_id: str

class DiagnosticReport(BaseModel):
    diagnoses: List[str]
    confidence_scores: List[float]
    recommended_tests: List[str]
    analysis_summary: str

class SymptomsList(BaseModel):
    primary_symptoms: List[str]
    secondary_symptoms: List[str]

app = FastAPI(title="Holistic Differential Diagnosis System")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db = MongoDB()
diagnosis_model = DiagnosisModel()
symptom_analyzer = SymptomAnalyzer()

@app.get("/api/patient/{patient_id}/history", response_model=PatientHistory)
async def get_patient_history(patient_id: str):
    """Get patient history including previous conditions."""
    try:
        patient_data = db.get_patient_history(patient_id)
        if "error" in patient_data:
            raise HTTPException(status_code=404, detail="Patient not found")
            
        # Ensure all required fields exist
        patient_data.setdefault("previous_conditions", [])
        patient_data.setdefault("current_medications", [])
        patient_data.setdefault("allergies", [])
        patient_data.setdefault("medical_history", [])
        
        return PatientHistory(**patient_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze", response_model=DiagnosticReport)
async def analyze_symptoms(symptom_input: SymptomInput):
    """Analyze symptoms and generate diagnostic report."""
    try:
        # Get patient history
        patient_history = db.get_patient_history(symptom_input.patient_id)
        if "error" in patient_history:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Analyze symptoms
        analyzed_symptoms = symptom_analyzer.analyze(
            symptom_input.primary_symptoms,
            symptom_input.secondary_symptoms
        )

        # Generate diagnosis using the model
        diagnosis_result = diagnosis_model.generate_diagnosis(
            analyzed_symptoms,
            patient_history
        )

        # Create diagnostic report
        report = DiagnosticReport(
            diagnoses=diagnosis_result["diagnoses"],
            confidence_scores=diagnosis_result["confidence_scores"],
            recommended_tests=diagnosis_result["recommended_tests"],
            analysis_summary=diagnosis_result["analysis_summary"]
        )

        # Save the diagnosis to database
        db.save_diagnosis(symptom_input.patient_id, {
            "date": datetime.now(),
            "primary_symptoms": symptom_input.primary_symptoms,
            "secondary_symptoms": symptom_input.secondary_symptoms,
            "diagnoses": diagnosis_result["diagnoses"],
            "confidence_scores": diagnosis_result["confidence_scores"],
            "recommended_tests": diagnosis_result["recommended_tests"],
            "analysis_summary": diagnosis_result["analysis_summary"]
        })

        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/symptoms", response_model=SymptomsList)
async def get_available_symptoms():
    """Get all available symptoms categorized as primary and secondary."""
    try:
        symptoms = diagnosis_model.get_all_symptoms()
        return SymptomsList(**symptoms)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
