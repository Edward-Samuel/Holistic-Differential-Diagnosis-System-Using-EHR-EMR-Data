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

## Setup Instructions for New Users

### 1. Prerequisites

- Python 3.8 or higher installed on your computer
- MongoDB installed locally
- Basic knowledge of running commands in terminal/command prompt

### 2. Installation Steps

#### Step 1: Download the Project

Clone or download this repository to your local machine.

#### Step 2: Install Required Python Packages

Open a command prompt or terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

This will install all necessary Python libraries for the application.

#### Step 3: Set Up MongoDB

1. Make sure MongoDB is installed on your system
2. Start MongoDB service:
   - On Windows:
   ```bash
   "C:\Program Files\MongoDB\Server\[version]\bin\mongod.exe" --dbpath="C:\data\db"
   ```
   - On macOS/Linux:
   ```bash
   mongod --dbpath /data/db
   ```
3. Initialize the database with sample data (optional):
   ```bash
   python database/init_database.py
   ```

#### Step 4: Configure API Keys

1. Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

   - Sign in with your Google account
   - Create a new API key
   - Copy the key to your clipboard

2. Create a `config.py` file in the project root directory with the following content:

   ```python
   GEMINI_API_KEY = 'your_api_key_here'

   # Email configuration (optional, for report emailing feature)
   SMTP_CONFIG = {
       'server': 'smtp.example.com',
       'port': 587,
       'username': 'your_email@example.com',
       'password': 'your_email_password',
       'use_tls': True
   }
   ```

   Replace 'your_api_key_here' with the API key you obtained from Google AI Studio.

#### Step 5: Run the Application

Start the application by running:

```bash
python app.py
```

The application will start and be accessible at http://localhost:8000 in your web browser.

### 3. Using the Application

#### Accessing the Web Interface

1. Open your web browser and navigate to http://localhost:8000
2. You'll see the main dashboard of the diagnostic system

#### Creating a New Diagnosis

1. Select a patient ID from the dropdown or create a new patient
2. Enter primary symptoms (required) and secondary symptoms (optional)
3. Click "Analyze Symptoms" to generate a diagnosis
4. Review the diagnostic report showing possible conditions, confidence scores, and recommended tests

#### Viewing Patient History

1. Select a patient ID from the dropdown
2. Click "View History" to see previous conditions, medications, and past diagnoses

#### Generating Reports

1. After a diagnosis is complete, click "Generate Report"
2. Choose to save the report to the database, download it as a PDF, or email it to a specified address

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

## Troubleshooting

- **MongoDB Connection Error**: Ensure MongoDB is running and accessible at localhost:27017
- **API Key Issues**: Verify your Gemini API key is correctly entered in config.py
- **Missing Dependencies**: Run `pip install -r requirements.txt` again to ensure all packages are installed
- **Application Crashes**: Check the console output for error messages

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
