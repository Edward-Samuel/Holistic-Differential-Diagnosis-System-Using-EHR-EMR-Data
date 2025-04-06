from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import io
from datetime import datetime

import pymongo
from models.diagnosis import DiagnosisModel
from database.mongodb import MongoDB
from utils.symptom_analyzer import SymptomAnalyzer
from utils.report_generator import DiagnosticReportGenerator
from config import SMTP_CONFIG  # You'll need to add this to config.py

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
report_generator = DiagnosticReportGenerator(email_config=SMTP_CONFIG)

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

@app.post("/generate-report/{patient_id}")
async def generate_diagnostic_report(
    patient_id: str,
    background_tasks: BackgroundTasks,
    email_to: str = None,
    store: bool = True
) -> Dict:
    """Generate a diagnostic report and optionally email/store it"""
    try:
        # Get patient data
        patient_data = db.get_patient_history(patient_id)
        if "error" in patient_data:
            raise HTTPException(status_code=404, detail="Patient not found")
            
        # Get latest diagnosis
        diagnoses = db.get_patient_diagnoses(patient_id)
        if not diagnoses:
            raise HTTPException(status_code=404, detail="No diagnosis found")
            
        latest_diagnosis = diagnoses[0]  # Assuming sorted by date
        
        # Generate PDF report
        pdf_data = report_generator.generate_report(
            patient_data=patient_data,
            primary_symptoms=latest_diagnosis.get("primary_symptoms", []),
            secondary_symptoms=latest_diagnosis.get("secondary_symptoms", []),
            diagnoses=latest_diagnosis.get("diagnoses", []),
            confidence_scores=latest_diagnosis.get("confidence_scores", []),
            recommended_tests=latest_diagnosis.get("recommended_tests", []),
            analysis_summary=latest_diagnosis.get("notes", "No summary available")
        )
        
        response_data = {"status": "success"}
        
        # Store in GridFS if requested
        if store:
            file_id = db.save_report_pdf(
                patient_id=patient_id,
                pdf_data=pdf_data,
                report_date=datetime.now()
            )
            response_data["file_id"] = file_id
            
        # Send email in background if requested
        if email_to:
            background_tasks.add_task(
                report_generator.email_report,
                email_to,
                pdf_data,
                patient_data.get("name", f"Patient {patient_id}")
            )
            response_data["email_status"] = "sending"
            
        # Return PDF as download if not storing or emailing
        if not (store or email_to):
            return StreamingResponse(
                io.BytesIO(pdf_data),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=report_{patient_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
                }
            )
            
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/{patient_id}")
async def get_patient_reports(patient_id: str) -> List[Dict]:
    """Get list of stored reports for a patient"""
    return db.get_patient_reports(patient_id)

@app.get("/reports/download/{file_id}")
async def download_report(file_id: str):
    """Download a specific report by file ID"""
    pdf_data = db.get_report_pdf(file_id)
    if not pdf_data:
        raise HTTPException(status_code=404, detail="Report not found")
        
    return StreamingResponse(
        io.BytesIO(pdf_data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=report_{file_id}.pdf"
        }
    )

@app.get("/download-report/{patient_id}")
async def download_diagnostic_report(patient_id: str) -> StreamingResponse:
    """Generate and download a diagnostic report"""
    try:
        # Get patient data
        patient_data = db.get_patient_history(patient_id)
        if "error" in patient_data:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Get latest diagnosis
        diagnoses = db.get_patient_diagnoses(patient_id)
        if not diagnoses:
            raise HTTPException(status_code=404, detail="No diagnosis found")

        latest_diagnosis = diagnoses[0]  # Assuming sorted by date

        # Generate PDF report
        pdf_data = report_generator.generate_report(
            patient_data=patient_data,
            primary_symptoms=latest_diagnosis.get("primary_symptoms", []),
            secondary_symptoms=latest_diagnosis.get("secondary_symptoms", []),
            diagnoses=latest_diagnosis.get("diagnoses", []),
            confidence_scores=latest_diagnosis.get("confidence_scores", []),
            recommended_tests=latest_diagnosis.get("recommended_tests", []),
            analysis_summary=latest_diagnosis.get("notes", "No summary available")
        )

        # Return PDF as a downloadable file
        return StreamingResponse(
            io.BytesIO(pdf_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_{patient_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
