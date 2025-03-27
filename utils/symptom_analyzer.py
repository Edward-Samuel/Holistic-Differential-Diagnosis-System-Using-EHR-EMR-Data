from typing import Dict, List, Any
import json
import google.generativeai as genai
from datetime import datetime
from config import GEMINI_API_KEY

class SymptomAnalyzer:
    def __init__(self):
        """Initialize the symptom analyzer"""
        self.symptom_severity = self._load_symptom_severity()
        
        try:
            # Configure Gemini
            genai.configure(api_key=GEMINI_API_KEY)
            
            # List available models
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"Found model: {m.name}")
            
            # Use gemini-1.5-pro model
            self.model = genai.GenerativeModel('models/gemini-1.5-pro')
            
            # Test the model
            response = self.model.generate_content("Hello")
            print("Gemini model initialized successfully")
            
        except Exception as e:
            print(f"Error initializing Gemini: {e}")
            self.model = None
        
        # Set default generation config
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1024,
        }

    def analyze(self, primary_symptoms: List[str], secondary_symptoms: List[str], patient_history: Dict = None) -> Dict:
        """
        Analyze primary and secondary symptoms using Gemini LLM
        """
        # Ensure symptoms are in the correct format
        primary = [s.strip() for s in primary_symptoms if s.strip()]
        secondary = [s.strip() for s in secondary_symptoms if s.strip()]
        
        # If Gemini is not available, use traditional analysis
        if not self.model:
            return self._traditional_analysis(primary, secondary, patient_history)
        
        # Prepare the prompt for Gemini with patient history
        prompt = self._create_analysis_prompt(primary, secondary, patient_history)
        
        try:
            # Get analysis from Gemini with specific configuration
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Check if response has content
            if not response or not hasattr(response, 'text'):
                raise Exception("No response from Gemini")
                
            analysis = self._parse_gemini_response(response.text)
            
            # Calculate severity scores
            severity_scores = self._calculate_severity(primary, secondary)
            
            # Find symptom relationships
            relationships = self._find_relationships(primary + secondary)
            
            return {
                "primary": primary,
                "secondary": secondary,
                "severity_scores": severity_scores,
                "relationships": relationships,
                "overall_severity": self._calculate_overall_severity(severity_scores),
                "gemini_analysis": analysis,
                "patient_history_analysis": analysis.get("history_analysis", {})
            }
        except Exception as e:
            print(f"Error in Gemini analysis: {e}")
            return self._traditional_analysis(primary, secondary, patient_history)

    def _traditional_analysis(self, primary: List[str], secondary: List[str], patient_history: Dict = None) -> Dict:
        """Fallback method for traditional symptom analysis"""
        severity_scores = self._calculate_severity(primary, secondary)
        relationships = self._find_relationships(primary + secondary)
        
        # Include basic history analysis
        history_analysis = {
            "previous_conditions_impact": "Unable to analyze impact of previous conditions",
            "medication_interactions": "Unable to analyze medication interactions",
            "risk_factors": []
        }
        
        if patient_history and "previous_conditions" in patient_history:
            history_analysis["risk_factors"] = patient_history["previous_conditions"]
        
        return {
            "primary": primary,
            "secondary": secondary,
            "severity_scores": severity_scores,
            "relationships": relationships,
            "overall_severity": self._calculate_overall_severity(severity_scores),
            "error": "Using traditional analysis due to Gemini API issues",
            "patient_history_analysis": history_analysis
        }

    def _load_symptom_severity(self) -> Dict[str, Dict[str, float]]:
        """Load symptom severity from disease_symptoms.json"""
        try:
            with open('disease_symptoms.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                severity = {}
                # Extract unique symptoms from all symptom strings
                for disease_data in data:
                    # Each disease data is a list where first element is disease info
                    if not isinstance(disease_data, list) or len(disease_data) == 0:
                        continue
                    disease_info = disease_data[0]
                    if not isinstance(disease_info, dict):
                        continue
                    # Look for symptom strings in the disease info
                    for value in disease_info.values():
                        if isinstance(value, str):
                            # Split the symptom string and clean each symptom
                            symptoms = [s.strip() for s in value.split(",") if s.strip()]
                            for symptom in symptoms:
                                if symptom and symptom not in severity:
                                    severity[symptom] = {
                                        "standard_name": symptom,
                                        "severity": 0.5  # Default severity
                                    }
                return severity
        except Exception as e:
            print(f"Error loading symptom severity: {e}")
            return {}

    def _create_analysis_prompt(self, primary_symptoms: List[str], secondary_symptoms: List[str], patient_history: Dict = None) -> str:
        """Create a prompt for Gemini analysis"""
        # Format patient history information
        history_section = ""
        if patient_history:
            history_section = "\nPatient History:\n"
            if "previous_conditions" in patient_history and patient_history["previous_conditions"]:
                history_section += "Previous Conditions:\n"
                for condition in patient_history["previous_conditions"]:
                    history_section += f"- {condition}\n"
            
            if "current_medications" in patient_history and patient_history["current_medications"]:
                history_section += "\nCurrent Medications:\n"
                for med in patient_history["current_medications"]:
                    history_section += f"- {med}\n"
            
            if "allergies" in patient_history and patient_history["allergies"]:
                history_section += "\nAllergies:\n"
                for allergy in patient_history["allergies"]:
                    history_section += f"- {allergy}\n"

        prompt = f"""Act as a medical expert system analyzing patient symptoms and history. Consider the patient's history first, then analyze how current symptoms might relate to or differ from previous conditions.

{history_section}
Current Symptoms:
Primary (More Severe) Symptoms:
{', '.join(primary_symptoms) if primary_symptoms else 'None reported'}

Secondary (Less Severe) Symptoms:
{', '.join(secondary_symptoms) if secondary_symptoms else 'None reported'}

Provide your analysis in the following JSON format:
{{
    "possible_conditions": [
        {{
            "name": "condition_name",
            "confidence": 0.XX,  // Probability between 0 and 1
            "description": "Brief description of the condition",
            "recommended_tests": ["test1", "test2"],
            "relation_to_history": "Explanation of how this relates to patient history (if applicable)"
        }}
    ],
    "severity_assessment": "Detailed assessment of overall symptom severity",
    "urgent_care_needed": true/false,  // Whether immediate medical attention is required
    "recommendations": [
        "Specific action items or recommendations",
        "Additional recommendations if any"
    ],
    "differential_notes": "Important notes about differential diagnosis and potential complications",
    "history_analysis": {{
        "previous_conditions_impact": "Analysis of how previous conditions might affect current symptoms",
        "medication_interactions": "Potential interactions with current medications",
        "risk_factors": ["List of identified risk factors based on history"]
    }}
}}

Important guidelines:
1. First analyze how current symptoms relate to patient history
2. Consider potential complications due to previous conditions
3. Check for medication interactions or contraindications
4. Base confidence scores on both history and current symptoms
5. Include at least 2-3 possible conditions when applicable
6. Be specific with test recommendations
7. Clearly indicate if urgent care is needed
8. Provide actionable recommendations
9. Format output as valid JSON

Analyze the patient's history and symptoms and provide your response:"""

        return prompt

    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse the response from Gemini into a structured format"""
        try:
            # Try to parse as JSON first
            # Find the JSON block in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                raise json.JSONDecodeError("No JSON found", response_text, 0)
                
            # Validate required fields
            required_fields = ["possible_conditions", "severity_assessment", "urgent_care_needed", 
                             "recommendations", "differential_notes", "history_analysis"]
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = [] if field in ["possible_conditions", "recommendations"] else ""
            
            # Ensure proper confidence values
            for condition in analysis["possible_conditions"]:
                if "confidence" in condition:
                    try:
                        condition["confidence"] = float(condition["confidence"])
                        condition["confidence"] = max(0.0, min(1.0, condition["confidence"]))
                    except (ValueError, TypeError):
                        condition["confidence"] = 0.5
                else:
                    condition["confidence"] = 0.5
                    
            return analysis
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error parsing Gemini response: {e}")
            # Return a structured error response
            return {
                "possible_conditions": [{
                    "name": "Unable to determine",
                    "confidence": 0.5,
                    "description": "Could not analyze symptoms properly",
                    "recommended_tests": ["General physical examination"],
                    "relation_to_history": "Unknown"
                }],
                "severity_assessment": "Unable to assess severity - please consult a healthcare provider",
                "urgent_care_needed": False,
                "recommendations": ["Please consult with a healthcare provider for proper evaluation"],
                "differential_notes": "Error in analyzing symptoms. A direct medical consultation is recommended.",
                "history_analysis": {
                    "previous_conditions_impact": "Unknown",
                    "medication_interactions": "Unknown",
                    "risk_factors": []
                }
            }

    def _calculate_severity(self, primary: List[str], secondary: List[str]) -> Dict[str, float]:
        """Calculate severity scores for symptoms"""
        severity_scores = {}
        
        # Primary symptoms get higher base severity
        for symptom in primary:
            base_severity = self.symptom_severity.get(symptom, {}).get("severity", 0.5)
            severity_scores[symptom] = base_severity * 1.5  # 50% higher for primary
        
        # Secondary symptoms use base severity
        for symptom in secondary:
            severity_scores[symptom] = self.symptom_severity.get(symptom, {}).get("severity", 0.3)
        
        return severity_scores

    def _find_relationships(self, symptoms: List[str]) -> List[Dict[str, Any]]:
        """Find relationships between symptoms"""
        relationships = []
        for i, symptom1 in enumerate(symptoms):
            for symptom2 in symptoms[i+1:]:
                if self._are_related(symptom1, symptom2):
                    relationships.append({
                        "symptoms": [symptom1, symptom2],
                        "relationship_type": "co-occurring",
                        "strength": 0.7
                    })
        return relationships

    def _are_related(self, symptom1: str, symptom2: str) -> bool:
        """Check if two symptoms are related"""
        # This is a simplified implementation
        # In a real system, this would use medical knowledge or ML models
        return True if symptom1 and symptom2 else False

    def _calculate_overall_severity(self, severity_scores: Dict[str, float]) -> float:
        """Calculate overall severity score"""
        if not severity_scores:
            return 0.0
        return sum(severity_scores.values()) / len(severity_scores)
