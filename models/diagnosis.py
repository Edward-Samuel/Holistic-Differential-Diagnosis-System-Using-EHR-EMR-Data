from typing import Dict, List, Any
import numpy as np
import pandas as pd
import json
from pathlib import Path

class DiagnosisModel:
    def __init__(self):
        # Initialize empty attributes
        self.df = None
        self.diseases = []
        self.symptoms = []
        self.disease_symptom_map = {}
        self.dataset_stats = {}
        
        # Load dataset and disease-symptom mappings
        self.load_dataset()
        if self.df is not None:
            self.load_disease_symptoms()
        
    def load_dataset(self):
        """Load and preprocess the dataset"""
        try:
            # Try to load disease.csv
            disease_path = Path(__file__).parent.parent / 'dataset.csv'
            if disease_path.exists():
                # Load disease.csv which has diseases and symptoms columns
                # Use python engine and specify encoding to handle special characters
                self.df = pd.read_csv(disease_path, engine='python', encoding='utf-8')
                
                # Validate columns
                if not {'diseases', 'symptoms'}.issubset(self.df.columns):
                    raise ValueError("disease.csv must contain 'diseases' and 'symptoms' columns")
                
                # Get unique diseases and symptoms
                self.diseases = self.df['diseases'].unique().tolist()
                self.symptoms = self.df['symptoms'].unique().tolist()
                
                # Store relevant statistics
                self.dataset_stats = {
                    'total_cases': len(self.df),
                    'diseases_distribution': self.df['diseases'].value_counts().to_dict(),
                    'last_updated': pd.Timestamp.now()
                }
                
                print(f"Successfully loaded dataset with {len(self.df)} records")
                print(f"Found {len(self.diseases)} diseases and {len(self.symptoms)} symptoms")
                
            else:
                raise FileNotFoundError("disease.csv not found")
            
        except Exception as e:
            print(f"Error loading dataset: {str(e)}")
            self.df = None
            self.diseases = []
            self.symptoms = []
            self.dataset_stats = {}

    def load_disease_symptoms(self):
        """Load disease-symptom mappings from the analyzed data"""
        try:
            json_path = Path(__file__).parent.parent / 'disease_symptoms.json'
            with open(json_path, 'r') as f:
                self.disease_symptom_map = json.load(f)
        except FileNotFoundError:
            print("Disease symptoms mapping not found. Analyzing dataset...")
            self._analyze_dataset()
            
    def _analyze_dataset(self):
        """Analyze the dataset to create disease-symptom mappings"""
        if self.df is None:
            raise ValueError("Cannot analyze dataset: Dataset not loaded properly")
            
        self.disease_symptom_map = {}
        
        # Group by disease and get symptom frequencies
        for disease in self.diseases:
            disease_data = self.df[self.df['diseases'] == disease]
            
            # Count frequency of each symptom for this disease
            symptom_counts = disease_data['symptoms'].value_counts()
            total_instances = len(disease_data)
            
            # Calculate frequency ratio for each symptom
            symptoms = {}
            for symptom, count in symptom_counts.items():
                frequency = count / total_instances
                symptoms[symptom] = round(float(frequency), 2)
            
            # Sort symptoms by frequency
            sorted_symptoms = dict(sorted(symptoms.items(), key=lambda x: x[1], reverse=True))
            
            # Split into primary (top 60%) and secondary (bottom 40%) symptoms
            n_primary = max(1, int(len(sorted_symptoms) * 0.6))  # Ensure at least 1 primary symptom
            primary_symptoms = dict(list(sorted_symptoms.items())[:n_primary])
            secondary_symptoms = dict(list(sorted_symptoms.items())[n_primary:])
            
            self.disease_symptom_map[disease] = {
                "primary": primary_symptoms,
                "secondary": secondary_symptoms,
                "severity_weight": 0.8,  # Default severity weight
                "tests": []  # Can be populated with relevant tests later
            }
        
        # Save the analyzed data
        try:
            json_path = Path(__file__).parent.parent / 'disease_symptoms.json'
            with open(json_path, 'w') as f:
                json.dump(self.disease_symptom_map, f, indent=4)
            print(f"Saved disease-symptom mappings to {json_path}")
        except Exception as e:
            print(f"Warning: Could not save disease-symptom mappings: {str(e)}")

    def generate_diagnosis(self, analyzed_symptoms: Dict, patient_history: Dict) -> Dict[str, Any]:
        """Generate diagnosis based on analyzed symptoms and patient history"""
        # Get primary and secondary symptoms
        primary_symptoms = analyzed_symptoms.get("primary", [])
        secondary_symptoms = analyzed_symptoms.get("secondary", [])
        
        if not primary_symptoms and not secondary_symptoms:
            return {
                "diagnoses": ["Insufficient data"],
                "confidence_scores": [1.0],
                "recommended_tests": ["General physical examination"],
                "analysis_summary": "Insufficient symptoms to generate a specific diagnosis."
            }
        
        # Get Gemini analysis
        gemini_analysis = analyzed_symptoms.get("gemini_analysis", {})
        
        if not gemini_analysis or "error" in analyzed_symptoms:
            # Fallback to traditional analysis if Gemini fails
            return self._traditional_diagnosis(primary_symptoms, secondary_symptoms, patient_history)
        
        # Extract diagnoses and confidence scores from Gemini analysis
        possible_conditions = gemini_analysis.get("possible_conditions", [])
        diagnoses = []
        confidence_scores = []
        
        for condition in possible_conditions:
            diagnoses.append(condition["name"])
            confidence_scores.append(float(condition["confidence"]))
        
        if not diagnoses:
            return self._traditional_diagnosis(primary_symptoms, secondary_symptoms, patient_history)
        
        # Get recommended tests from Gemini
        recommended_tests = set()
        for condition in possible_conditions:
            recommended_tests.update(condition.get("recommended_tests", []))
        
        # Generate analysis summary
        analysis_summary = self._generate_analysis_summary_from_gemini(
            gemini_analysis,
            primary_symptoms,
            secondary_symptoms,
            patient_history
        )
        
        return {
            "diagnoses": diagnoses,
            "confidence_scores": confidence_scores,
            "recommended_tests": list(recommended_tests),
            "analysis_summary": analysis_summary,
            "severity_assessment": gemini_analysis.get("severity_assessment", ""),
            "urgent_care_needed": gemini_analysis.get("urgent_care_needed", False),
            "recommendations": gemini_analysis.get("recommendations", [])
        }
    
    def _traditional_diagnosis(self, primary_symptoms: List[str], secondary_symptoms: List[str], 
                             patient_history: Dict) -> Dict[str, Any]:
        """Fallback method using traditional analysis when Gemini is unavailable"""
        all_symptoms = primary_symptoms + secondary_symptoms
        symptom_str = ", ".join(all_symptoms)
        
        # Find matching diseases
        matching_diseases = []
        confidence_scores = []
        
        try:
            with open('disease_symptoms.json', 'r', encoding='utf-8') as f:
                diseases = json.load(f)
                for disease_data in diseases:
                    if not isinstance(disease_data, list) or len(disease_data) == 0:
                        continue
                    
                    disease_info = disease_data[0]
                    if not isinstance(disease_info, dict):
                        continue
                    
                    max_score = 0
                    disease_name = None
                    
                    for key, value in disease_info.items():
                        if isinstance(value, str):
                            score = self._calculate_similarity(symptom_str, value)
                            if score > max_score:
                                max_score = score
                                disease_name = key
                    
                    if max_score > 0.1 and disease_name:
                        matching_diseases.append(disease_name)
                        confidence_scores.append(max_score)
        except Exception as e:
            print(f"Error in traditional diagnosis: {e}")
            return {
                "diagnoses": ["Error"],
                "confidence_scores": [1.0],
                "recommended_tests": ["General physical examination"],
                "analysis_summary": "An error occurred while analyzing symptoms. Please try again."
            }
        
        if not matching_diseases:
            return {
                "diagnoses": ["Insufficient data"],
                "confidence_scores": [1.0],
                "recommended_tests": ["General physical examination"],
                "analysis_summary": "No specific diagnosis matches the provided symptoms. Please consult with a healthcare provider for a thorough evaluation."
            }
        
        # Sort by confidence score
        sorted_pairs = sorted(zip(matching_diseases, confidence_scores), 
                            key=lambda x: x[1], reverse=True)
        diagnoses, scores = zip(*sorted_pairs)
        
        return {
            "diagnoses": list(diagnoses),
            "confidence_scores": list(scores),
            "recommended_tests": self._get_recommended_tests(diagnoses[0]),
            "analysis_summary": self._generate_analysis_summary(
                diagnoses, scores, primary_symptoms, secondary_symptoms, patient_history
            )
        }
    
    def _generate_analysis_summary_from_gemini(self, gemini_analysis: Dict, 
                                             primary_symptoms: List[str],
                                             secondary_symptoms: List[str],
                                             patient_history: Dict) -> str:
        """Generate a comprehensive analysis summary using Gemini's output"""
        summary_parts = []
        
        # Add severity assessment
        severity = gemini_analysis.get("severity_assessment")
        if severity:
            summary_parts.append(f"Severity Assessment: {severity}")
        
        # Add urgent care recommendation if needed
        if gemini_analysis.get("urgent_care_needed"):
            summary_parts.append("\nURGENT CARE RECOMMENDED")
        
        # Add differential diagnosis notes
        diff_notes = gemini_analysis.get("differential_notes")
        if diff_notes:
            summary_parts.append(f"\nDifferential Diagnosis Notes: {diff_notes}")
        
        # Add recommendations
        recommendations = gemini_analysis.get("recommendations", [])
        if recommendations:
            summary_parts.append("\nRecommendations:")
            for rec in recommendations:
                summary_parts.append(f"• {rec}")
        
        # Add relevant patient history if available
        if patient_history:
            conditions = patient_history.get("previous_conditions", [])
            if conditions:
                summary_parts.append("\nRelevant Patient History:")
                for condition in conditions:
                    summary_parts.append(f"• Previous condition: {condition}")
        
        return "\n".join(summary_parts)

    def _calculate_similarity(self, symptom_str1: str, symptom_str2: str) -> float:
        """Calculate the similarity score between two symptom strings"""
        # Split into individual symptoms
        symptoms1 = set(s.strip().lower() for s in symptom_str1.split(","))
        symptoms2 = set(s.strip().lower() for s in symptom_str2.split(","))
        
        # Calculate Jaccard similarity
        intersection = len(symptoms1.intersection(symptoms2))
        union = len(symptoms1.union(symptoms2))
        
        return intersection / union if union > 0 else 0.0

    def _get_recommended_tests(self, diagnosis: str) -> List[str]:
        """Get recommended tests for a specific diagnosis"""
        # For demonstration purposes, this example returns a static list of tests
        # In a real-world application, this would be based on the diagnosis and patient history
        return ["General physical examination", "Blood work", "Imaging studies"]

    def _generate_analysis_summary(self, diagnoses: List[str], scores: List[float], 
                                 primary_symptoms: List[str], secondary_symptoms: List[str], 
                                 patient_history: Dict) -> str:
        """Generate a detailed analysis summary"""
        # For demonstration purposes, this example returns a simple summary string
        # In a real-world application, this would be based on the diagnoses, symptoms, and patient history
        summary = f"Based on the provided symptoms, the top diagnoses are: {', '.join(diagnoses)}"
        summary += f" with confidence scores: {', '.join(map(str, scores))}"
        summary += f" The primary symptoms are: {', '.join(primary_symptoms)}"
        summary += f" and the secondary symptoms are: {', '.join(secondary_symptoms)}"
        summary += f" The patient's history includes: {', '.join(patient_history.get('previous_conditions', []))}"
        return summary

    def get_all_symptoms(self) -> Dict[str, List[str]]:
        """Get all available symptoms categorized as primary and secondary."""
        # Create sets to store unique symptoms
        primary_symptoms = set()
        secondary_symptoms = set()
        
        # Process each disease's symptoms
        for disease_data in self.disease_symptom_map.values():
            # Add primary symptoms, ensuring they're normalized
            for symptom in disease_data["primary"].keys():
                normalized = symptom.strip().lower()
                if normalized:  # Only add non-empty symptoms
                    primary_symptoms.add(normalized)
            
            # Add secondary symptoms, ensuring they're normalized
            for symptom in disease_data["secondary"].keys():
                normalized = symptom.strip().lower()
                if normalized and normalized not in primary_symptoms:  # Avoid duplicates with primary
                    secondary_symptoms.add(normalized)
        
        # Convert to sorted lists and capitalize first letter of each word for display
        return {
            "primary_symptoms": sorted([s.title() for s in primary_symptoms]),
            "secondary_symptoms": sorted([s.title() for s in secondary_symptoms])
        }
