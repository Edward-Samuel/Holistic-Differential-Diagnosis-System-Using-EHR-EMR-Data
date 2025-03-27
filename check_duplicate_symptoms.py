import json
from pathlib import Path

def check_duplicate_symptoms():
    # Load disease symptoms
    json_path = Path('disease_symptoms.json')
    with open(json_path, 'r') as f:
        disease_symptom_map = json.load(f)
    
    duplicates_found = False
    
    # Check each disease
    for disease, data in disease_symptom_map.items():
        primary_symptoms = set(data.get('primary', {}).keys())
        secondary_symptoms = set(data.get('secondary', {}).keys())
        
        # Find intersection
        common_symptoms = primary_symptoms.intersection(secondary_symptoms)
        
        if common_symptoms:
            duplicates_found = True
            print(f"\nDisease: {disease}")
            print("Symptoms found in both primary and secondary categories:")
            for symptom in common_symptoms:
                print(f"  - {symptom}")
                print(f"    Primary frequency: {data['primary'][symptom]}")
                print(f"    Secondary frequency: {data['secondary'][symptom]}")
    
    if not duplicates_found:
        print("\nNo symptoms found that appear in both primary and secondary categories.")

if __name__ == '__main__':
    check_duplicate_symptoms()
