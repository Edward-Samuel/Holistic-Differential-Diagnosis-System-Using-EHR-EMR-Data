import streamlit as st
import requests
import json
import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict

# Configure the app
st.set_page_config(
    page_title="AI Differential Diagnosis System",
    page_icon="🏥",
    layout="wide"
)

# API endpoint
API_URL = "http://localhost:8000/api"

def get_patient_history(patient_id: str) -> Dict:
    """Fetch patient history from the API"""
    try:
        response = requests.get(f"{API_URL}/patient/{patient_id}/history")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching patient history: {str(e)}")
        return None

def format_symptom_for_display(symptom: str) -> str:
    """Format a symptom from database format to display format"""
    return symptom.replace('_', ' ').title()

def format_symptom_for_api(symptom: str) -> str:
    """Format a symptom from display format to database format"""
    return symptom.lower().replace(' ', '_')

def get_available_symptoms() -> Dict:
    """Fetch available symptoms from the API"""
    try:
        response = requests.get(f"{API_URL}/symptoms")
        if response.status_code == 200:
            data = response.json()
            # Format symptoms for display
            return {
                "primary_symptoms": [format_symptom_for_display(s) for s in data["primary_symptoms"]],
                "secondary_symptoms": [format_symptom_for_display(s) for s in data["secondary_symptoms"]]
            }
        st.error(f"Error fetching symptoms: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        st.error(f"Error fetching symptoms: {str(e)}")
        return None

def analyze_symptoms(symptoms_data: Dict) -> Dict:
    """Send symptoms to API for analysis"""
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            f"{API_URL}/analyze",
            json={
                "patient_id": symptoms_data["patient_id"],
                "primary_symptoms": [format_symptom_for_api(s) for s in symptoms_data["primary_symptoms"]],
                "secondary_symptoms": [format_symptom_for_api(s) for s in symptoms_data["secondary_symptoms"]]
            },
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error analyzing symptoms: {str(e)}")
        return None

def create_diagnosis_chart(diagnoses: List[str], probabilities: List[float]) -> go.Figure:
    """Create a bar chart for diagnosis probabilities"""
    # Format diagnoses to be more readable
    formatted_diagnoses = [d.replace('_', ' ').title() for d in diagnoses]
    
    # Format probabilities as percentages
    formatted_probabilities = [p * 100 for p in probabilities]
    
    fig = go.Figure(data=[
        go.Bar(
            x=formatted_probabilities,
            y=formatted_diagnoses,
            orientation='h',
            marker_color='rgb(26, 118, 255)',
            text=[f"{p:.1f}%" for p in formatted_probabilities],
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title={
            'text': "Differential Diagnosis Probabilities",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title="Confidence Score (%)",
        yaxis_title="Potential Diagnosis",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12)
    )
    
    # Update axes
    fig.update_xaxes(range=[0, 100], gridcolor='rgba(128,128,128,0.2)', ticksuffix='%')
    fig.update_yaxes(gridcolor='rgba(128,128,128,0.2)')
    
    return fig

def main():
    st.title("AI-Powered Differential Diagnosis System")
    
    # Fetch available symptoms
    available_symptoms = get_available_symptoms()
    if not available_symptoms:
        st.error("Could not load symptoms. Please try again later.")
        return
    
    # Sidebar for patient information
    with st.sidebar:
        st.header("Patient Information")
        patient_id = st.text_input("Patient ID", value="DEMO123")
        
        if patient_id:
            patient_data = get_patient_history(patient_id)
            if patient_data and "error" not in patient_data:
                st.success("Patient found")
                
                # Display previous conditions
                if "previous_conditions" in patient_data and patient_data["previous_conditions"]:
                    st.subheader("Previous Conditions")
                    for condition in patient_data["previous_conditions"]:
                        st.write(f"• {condition}")
                
                # Display current medications if available
                if "current_medications" in patient_data and patient_data["current_medications"]:
                    st.subheader("Current Medications")
                    for med in patient_data["current_medications"]:
                        st.write(f"• {med}")
                
                # Display allergies if available
                if "allergies" in patient_data and patient_data["allergies"]:
                    st.subheader("Allergies")
                    for allergy in patient_data["allergies"]:
                        st.write(f"• {allergy}")
            else:
                st.info("Using demo patient data")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Symptom Input")
        
        # Symptom input with dynamically loaded options
        primary_symptoms = st.multiselect(
            "Primary Symptoms",
            options=available_symptoms["primary_symptoms"],
            help="Select the main symptoms that are most severe or concerning"
        )
        
        secondary_symptoms = st.multiselect(
            "Secondary Symptoms",
            options=available_symptoms["secondary_symptoms"],
            help="Select any additional symptoms that are less severe"
        )
        
        if st.button("Analyze Symptoms", type="primary"):
            if not primary_symptoms:
                st.warning("Please select at least one primary symptom")
            else:
                with st.spinner("Analyzing symptoms..."):
                    analysis_result = analyze_symptoms({
                        "patient_id": patient_id,
                        "primary_symptoms": primary_symptoms,
                        "secondary_symptoms": secondary_symptoms
                    })
                    
                    if analysis_result:
                        # Create an expander for the analysis details
                        with st.expander("Analysis Details", expanded=True):
                            # Display diagnosis chart
                            st.plotly_chart(create_diagnosis_chart(
                                analysis_result.get("diagnoses", []),
                                analysis_result.get("confidence_scores", [])
                            ), use_container_width=True)
                            
                            # Display recommendations
                            st.subheader("Recommended Tests")
                            for test in analysis_result.get("recommended_tests", []):
                                st.write(f"• {test}")
                            
                            # Display analysis summary
                            st.subheader("Analysis Summary")
                            st.write(analysis_result.get("analysis_summary", ""))
                            
                            # Display selected symptoms
                            st.subheader("Selected Symptoms")
                            if primary_symptoms:
                                st.write("**Primary Symptoms:**")
                                for symptom in primary_symptoms:
                                    st.write(f"• {symptom}")
                            if secondary_symptoms:
                                st.write("**Secondary Symptoms:**")
                                for symptom in secondary_symptoms:
                                    st.write(f"• {symptom}")
                    else:
                        st.error("Error analyzing symptoms")
    
    with col2:
        st.header("Patient History Timeline")
        if patient_id and patient_data and "error" not in patient_data:
            if "medical_history" in patient_data and patient_data["medical_history"]:
                # Convert medical history to DataFrame
                history_df = pd.DataFrame(patient_data["medical_history"])
                history_df["date"] = pd.to_datetime(history_df["date"])
                history_df = history_df.sort_values("date", ascending=False)
                
                # Display timeline
                for _, entry in history_df.iterrows():
                    with st.expander(f"{entry['date'].strftime('%Y-%m-%d')} - {entry['type']}"):
                        st.write(f"**Symptoms:** {', '.join(entry['symptoms'])}")
                        st.write(f"**Diagnosis:** {entry['diagnosis']}")
                        st.write(f"**Medications:** {', '.join(entry['prescribed_medications'])}")
                        if "notes" in entry:
                            st.write(f"**Notes:** {entry['notes']}")

if __name__ == "__main__":
    main()
