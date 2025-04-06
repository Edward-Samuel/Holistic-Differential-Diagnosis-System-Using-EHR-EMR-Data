from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from datetime import datetime
import os
from typing import Dict, List, Optional
import io
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

class DiagnosticReportGenerator:
    def __init__(self, email_config: Optional[Dict] = None):
        self.styles = getSampleStyleSheet()
        self.logo_path = os.path.join(Path(__file__).parent.parent, "static", "logo.png")
        self.email_config = email_config

    def _create_header(self, doc, patient_data: Dict) -> List:
        """Create the report header with hospital logo and patient info"""
        elements = []
        
        if os.path.exists(self.logo_path):
            img = Image(self.logo_path, width=2*inch, height=1*inch)
            elements.append(img)
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30
        )
        elements.append(Paragraph("Diagnostic Assessment Report", title_style))
        
        patient_info = [
            ["Patient ID:", patient_data.get("patient_id", "N/A")],
            ["Date:", datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["Name:", patient_data.get("name", "N/A")],
            ["Age:", patient_data.get("age", "N/A")],
            ["Gender:", patient_data.get("gender", "N/A")]
        ]
        
        t = Table(patient_info, colWidths=[2*inch, 4*inch])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))
        return elements

    def _create_medical_history_section(self, medical_history: List[Dict]) -> List:
        """Create the medical history section"""
        elements = []
        elements.append(Paragraph("Medical History", self.styles["Heading2"]))
        
        if not medical_history:
            elements.append(Paragraph("No previous medical history available", self.styles["Normal"]))
            return elements
        
        # Sort history by date
        sorted_history = sorted(medical_history, key=lambda x: x['date'], reverse=True)
        
        # Create table data
        history_data = [[
            "Date", "Type", "Symptoms", "Diagnosis", "Medications"
        ]]
        
        for entry in sorted_history[:5]:  # Show last 5 entries
            history_data.append([
                entry.get('date', '').split('T')[0],
                entry.get('type', 'N/A'),
                "\n".join(entry.get('symptoms', [])),
                entry.get('diagnosis', 'N/A'),
                "\n".join(entry.get('prescribed_medications', []))
            ])
        
        t = Table(history_data, colWidths=[1*inch, 1*inch, 2*inch, 1.5*inch, 2*inch])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))
        return elements

    def _create_health_inferences_section(self, patient_data: Dict, current_diagnosis: Dict) -> List:
        """Create health inferences section"""
        elements = []
        elements.append(Paragraph("Health Inferences", self.styles["Heading2"]))
        
        # Compile key health insights
        inferences = []
        
        # Check for chronic conditions
        if previous_conditions := patient_data.get('previous_conditions', []):
            inferences.append(f"Chronic Conditions: {', '.join(previous_conditions)}")
            
        # Medication analysis
        if current_meds := patient_data.get('current_medications', []):
            inferences.append(f"Current Medications: {', '.join(current_meds)}")
            
        # Allergies
        if allergies := patient_data.get('allergies', []):
            inferences.append(f"Known Allergies: {', '.join(allergies)}")
            
        # Pattern analysis from symptoms
        primary_symptoms = current_diagnosis.get('primary_symptoms', [])
        if len(primary_symptoms) > 2:
            inferences.append(f"Multiple presenting symptoms suggest complex condition")
            
        # Create bulleted list
        for inference in inferences:
            elements.append(Paragraph(f"• {inference}", self.styles["Normal"]))
            
        elements.append(Spacer(1, 20))
        return elements

    def _create_symptoms_section(self, primary_symptoms: List[str], secondary_symptoms: List[str]) -> List:
        """Create the symptoms section"""
        elements = []
        elements.append(Paragraph("Symptoms", self.styles["Heading2"]))
        
        symptoms_data = [["Primary Symptoms:", "\n".join([f"• {s}" for s in primary_symptoms])]]
        if secondary_symptoms:
            symptoms_data.append(["Secondary Symptoms:", "\n".join([f"• {s}" for s in secondary_symptoms])])
        
        t = Table(symptoms_data, colWidths=[2*inch, 4*inch])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))
        return elements

    def _create_diagnosis_chart(self, diagnoses: List[str], confidence_scores: List[float]) -> Drawing:
        """Create a horizontal bar chart for diagnosis probabilities"""
        drawing = Drawing(400, 200)
        
        bc = HorizontalBarChart()
        bc.x = 50
        bc.y = 50
        bc.height = 125
        bc.width = 300
        bc.data = [confidence_scores]
        bc.categoryAxis.categoryNames = diagnoses
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = 100
        bc.valueAxis.valueStep = 20
        bc.bars[0].fillColor = colors.blue
        
        drawing.add(bc)
        return drawing

    def generate_report(self, 
                       patient_data: Dict, 
                       primary_symptoms: List[str],
                       secondary_symptoms: List[str],
                       diagnoses: List[str],
                       confidence_scores: List[float],
                       recommended_tests: List[str],
                       analysis_summary: str) -> bytes:
        """Generate a PDF report and return it as bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        elements = []
        
        # Add header
        elements.extend(self._create_header(doc, patient_data))
        
        # Add medical history if available
        if medical_history := patient_data.get('medical_history'):
            elements.extend(self._create_medical_history_section(medical_history))
        
        # Add symptoms section
        elements.extend(self._create_symptoms_section(primary_symptoms, secondary_symptoms))
        
        # Add diagnosis section
        elements.append(Paragraph("Differential Diagnosis", self.styles["Heading2"]))
        elements.append(self._create_diagnosis_chart(diagnoses, confidence_scores))
        elements.append(Spacer(1, 20))
        
        # Add health inferences
        elements.extend(self._create_health_inferences_section(
            patient_data, 
            {
                "primary_symptoms": primary_symptoms,
                "secondary_symptoms": secondary_symptoms,
                "diagnoses": diagnoses,
                "confidence_scores": confidence_scores
            }
        ))
        
        # Add recommended tests
        elements.append(Paragraph("Recommended Tests", self.styles["Heading2"]))
        tests_list = "\n".join([f"• {test}" for test in recommended_tests])
        elements.append(Paragraph(tests_list, self.styles["Normal"]))
        elements.append(Spacer(1, 20))
        
        # Add analysis summary
        elements.append(Paragraph("Analysis Summary", self.styles["Heading2"]))
        elements.append(Paragraph(analysis_summary, self.styles["Normal"]))
        
        # Build PDF
        doc.build(elements)
        return buffer.getvalue()

    def email_report(self, recipient_email: str, pdf_data: bytes, patient_name: str) -> bool:
        """Email the PDF report"""
        if not self.email_config:
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender']
            msg['To'] = recipient_email
            msg['Subject'] = f'Diagnostic Report - {patient_name}'
            
            msg.attach(MIMEText('Please find attached the diagnostic report.'))
            
            pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
            pdf_attachment.add_header(
                'Content-Disposition', 
                'attachment', 
                filename=f'diagnostic_report_{datetime.now().strftime("%Y%m%d")}.pdf'
            )
            msg.attach(pdf_attachment)
            
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)
                
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False