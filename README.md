# AI-Powered Holistic Differential Diagnosis System

A standalone diagnostic support system that runs entirely on a local machine, integrating EHR/EMR data analysis with AI-driven diagnosis using Google's Gemini LLM.

## Features
- Advanced Symptom Analysis using Gemini LLM
- Historical Data Integration and Analysis
- Holistic Patient History Consideration
- AI-Driven Differential Diagnosis
- Medication Interaction Checks
- Severity Assessment and Urgent Care Detection
- Automated Test Recommendations
- Interactive Clinician Dashboard

## Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure API Keys:
   - Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a `config.py` file with your API key:
     ```python
     GEMINI_API_KEY = 'your_api_key_here'
     ```

3. Start MongoDB locally

4. Run the application:
```bash
python app.py
```

## Components
- `utils/symptom_analyzer.py`: Core symptom analysis using Gemini LLM
- `models/diagnosis.py`: Diagnosis generation and scoring
- `database/mongodb.py`: Database interactions
- `frontend/app.py`: Web interface
- `config.py`: Configuration settings (not tracked in git)

## Key Features
### Holistic Analysis
- Prioritizes patient history in diagnosis
- Considers previous conditions
- Checks medication interactions
- Analyzes symptom relationships

### AI Integration
- Uses Gemini 1.5 Pro for advanced analysis
- Fallback to traditional analysis if needed
- Structured JSON responses
- Confidence scoring

### Safety Features
- Urgent care detection
- Risk factor identification
- Medication contraindication warnings
- Automated severity assessment

## API Response Format
```json
{
    "possible_conditions": [
        {
            "name": "condition_name",
            "confidence": 0.XX,
            "description": "description",
            "recommended_tests": ["test1", "test2"],
            "relation_to_history": "history analysis"
        }
    ],
    "severity_assessment": "detailed assessment",
    "urgent_care_needed": true/false,
    "recommendations": ["action items"],
    "differential_notes": "important notes",
    "history_analysis": {
        "previous_conditions_impact": "analysis",
        "medication_interactions": "analysis",
        "risk_factors": ["risk factors"]
    }
}
```

## Contributing
Please ensure you don't commit any sensitive information or API keys.

## License
MIT License
