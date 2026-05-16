"""
Seed Data Generator
Creates synthetic patient records and clinical risk scoring rules.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


PATIENTS = {
    "P001": {
        "patient_id": "P001",
        "name": "Rajesh Kumar",
        "age": 58,
        "gender": "Male",
        "blood_group": "B+",
        "demographics": {
            "height_cm": 170,
            "weight_kg": 85,
            "bmi": 29.4,
        },
        "vitals_latest": {
            "blood_pressure_systolic": 155,
            "blood_pressure_diastolic": 95,
            "heart_rate": 88,
            "temperature_celsius": 37.1,
            "spo2": 96,
            "respiratory_rate": 18,
            "recorded_at": "2026-04-09T14:30:00",
        },
        "medical_history": [
            {
                "condition": "Type 2 Diabetes Mellitus",
                "diagnosed_year": 2018,
                "status": "ongoing",
                "medications": ["Metformin 500mg BD", "Glimepiride 2mg OD"],
            },
            {
                "condition": "Hypertension",
                "diagnosed_year": 2016,
                "status": "ongoing",
                "medications": ["Amlodipine 5mg OD", "Telmisartan 40mg OD"],
            },
            {
                "condition": "Hyperlipidemia",
                "diagnosed_year": 2020,
                "status": "ongoing",
                "medications": ["Atorvastatin 20mg OD"],
            },
        ],
        "allergies": ["Penicillin", "Sulfonamides"],
        "surgical_history": ["Appendectomy (2005)"],
        "family_history": [
            "Father: Myocardial Infarction at age 55",
            "Mother: Type 2 Diabetes",
        ],
        "lab_results_recent": {
            "HbA1c": {"value": 7.8, "unit": "%", "reference": "< 7.0", "date": "2026-03-15"},
            "LDL_cholesterol": {"value": 145, "unit": "mg/dL", "reference": "< 100", "date": "2026-03-15"},
            "HDL_cholesterol": {"value": 38, "unit": "mg/dL", "reference": "> 40", "date": "2026-03-15"},
            "Triglycerides": {"value": 210, "unit": "mg/dL", "reference": "< 150", "date": "2026-03-15"},
            "Creatinine": {"value": 1.2, "unit": "mg/dL", "reference": "0.7-1.3", "date": "2026-03-15"},
            "Troponin_I": {"value": 0.02, "unit": "ng/mL", "reference": "< 0.04", "date": "2026-04-09"},
        },
        "current_complaints": [
            "Chest tightness on exertion for 2 weeks",
            "Occasional breathlessness climbing stairs",
            "Mild epigastric discomfort",
        ],
    },
    "P002": {
        "patient_id": "P002",
        "name": "Lakshmi Devi",
        "age": 72,
        "gender": "Female",
        "blood_group": "O+",
        "demographics": {
            "height_cm": 155,
            "weight_kg": 62,
            "bmi": 25.8,
        },
        "vitals_latest": {
            "blood_pressure_systolic": 148,
            "blood_pressure_diastolic": 88,
            "heart_rate": 82,
            "temperature_celsius": 36.8,
            "spo2": 94,
            "respiratory_rate": 20,
            "recorded_at": "2026-04-09T10:15:00",
        },
        "medical_history": [
            {
                "condition": "Atrial Fibrillation",
                "diagnosed_year": 2022,
                "status": "ongoing",
                "medications": ["Apixaban 5mg BD"],
            },
            {
                "condition": "Congestive Heart Failure (NYHA II)",
                "diagnosed_year": 2023,
                "status": "ongoing",
                "medications": ["Furosemide 40mg OD", "Carvedilol 6.25mg BD", "Ramipril 5mg OD"],
            },
            {
                "condition": "Chronic Kidney Disease Stage 3",
                "diagnosed_year": 2024,
                "status": "ongoing",
                "medications": [],
            },
        ],
        "allergies": ["Aspirin (GI bleeding)", "Iodine contrast"],
        "surgical_history": ["Total knee replacement - Right (2019)"],
        "family_history": [
            "Mother: Stroke at age 68",
            "Sister: Atrial Fibrillation",
        ],
        "lab_results_recent": {
            "BNP": {"value": 450, "unit": "pg/mL", "reference": "< 100", "date": "2026-04-01"},
            "eGFR": {"value": 42, "unit": "mL/min", "reference": "> 60", "date": "2026-04-01"},
            "Creatinine": {"value": 1.6, "unit": "mg/dL", "reference": "0.6-1.1", "date": "2026-04-01"},
            "INR": {"value": 1.1, "unit": "", "reference": "0.9-1.1", "date": "2026-04-01"},
            "Hemoglobin": {"value": 10.8, "unit": "g/dL", "reference": "12-16", "date": "2026-04-01"},
        },
        "current_complaints": [
            "Increasing ankle swelling for 1 week",
            "Worsening breathlessness at rest",
            "Palpitations - irregular",
            "Fatigue and decreased appetite",
        ],
    },
    "P003": {
        "patient_id": "P003",
        "name": "Arjun Mehta",
        "age": 34,
        "gender": "Male",
        "blood_group": "A+",
        "demographics": {
            "height_cm": 178,
            "weight_kg": 72,
            "bmi": 22.7,
        },
        "vitals_latest": {
            "blood_pressure_systolic": 122,
            "blood_pressure_diastolic": 78,
            "heart_rate": 74,
            "temperature_celsius": 37.0,
            "spo2": 99,
            "respiratory_rate": 14,
            "recorded_at": "2026-04-10T09:00:00",
        },
        "medical_history": [
            {
                "condition": "Seasonal Allergic Rhinitis",
                "diagnosed_year": 2020,
                "status": "intermittent",
                "medications": ["Cetirizine 10mg PRN"],
            },
        ],
        "allergies": [],
        "surgical_history": [],
        "family_history": [
            "Father: Hypertension (controlled)",
            "No family history of cardiac disease",
        ],
        "lab_results_recent": {
            "CBC": {"value": "Normal", "unit": "", "reference": "Normal", "date": "2026-03-20"},
            "Lipid_panel": {"value": "Normal", "unit": "", "reference": "Normal", "date": "2026-03-20"},
            "Fasting_glucose": {"value": 92, "unit": "mg/dL", "reference": "70-100", "date": "2026-03-20"},
        },
        "current_complaints": [
            "Routine annual health checkup",
            "Occasional mild headaches - likely tension type",
        ],
    },
}


CLINICAL_RULES = {
    "HEART_score": {
        "name": "HEART Score for Chest Pain",
        "description": "Stratifies risk of Major Adverse Cardiac Events (MACE) in chest pain patients.",
        "applicable_conditions": ["chest pain", "chest tightness", "angina"],
        "scoring_criteria": {
            "History": {
                "0": "Slightly suspicious",
                "1": "Moderately suspicious",
                "2": "Highly suspicious",
            },
            "ECG": {
                "0": "Normal",
                "1": "Non-specific repolarization disturbance",
                "2": "Significant ST deviation",
            },
            "Age": {
                "0": "< 45 years",
                "1": "45-64 years",
                "2": ">= 65 years",
            },
            "Risk_factors": {
                "0": "No known risk factors",
                "1": "1-2 risk factors (HTN, DM, hyperlipidemia, obesity, smoking, family hx)",
                "2": "3+ risk factors or history of atherosclerotic disease",
            },
            "Troponin": {
                "0": "Normal (le 99th percentile)",
                "1": "1-3x normal",
                "2": "> 3x normal",
            },
        },
        "interpretation": {
            "0-3": {"risk": "Low", "mace_rate": "0.9-1.7%", "recommendation": "Consider early discharge with outpatient follow-up"},
            "4-6": {"risk": "Moderate", "mace_rate": "12-16.6%", "recommendation": "Admit for observation, serial troponins, cardiology consult"},
            "7-10": {"risk": "High", "mace_rate": "50-65%", "recommendation": "Urgent invasive strategy, early cardiology intervention"},
        },
    },
    "CHA2DS2_VASc": {
        "name": "CHA2DS2-VASc Score",
        "description": "Estimates stroke risk in patients with atrial fibrillation to guide anticoagulation therapy.",
        "applicable_conditions": ["atrial fibrillation", "AF", "a-fib"],
        "scoring_criteria": {
            "Congestive_Heart_Failure": {"0": "Absent", "1": "Present"},
            "Hypertension": {"0": "Absent", "1": "Present"},
            "Age_75_or_older": {"0": "No", "2": "Yes"},
            "Diabetes_Mellitus": {"0": "Absent", "1": "Present"},
            "Stroke_TIA_history": {"0": "No", "2": "Yes"},
            "Vascular_disease": {"0": "Absent", "1": "Present (prior MI, PAD, aortic plaque)"},
            "Age_65_74": {"0": "No", "1": "Yes"},
            "Sex_category_female": {"0": "Male", "1": "Female"},
        },
        "interpretation": {
            "0": {"risk": "Low", "annual_stroke_rate": "0%", "recommendation": "No anticoagulation needed (male); reassess (female with score 1)"},
            "1": {"risk": "Low-Moderate", "annual_stroke_rate": "1.3%", "recommendation": "Consider oral anticoagulation (OAC)"},
            "2": {"risk": "Moderate", "annual_stroke_rate": "2.2%", "recommendation": "Oral anticoagulation recommended"},
            "3+": {"risk": "Moderate-High", "annual_stroke_rate": "3.2-15.2%", "recommendation": "Oral anticoagulation strongly recommended"},
        },
    },
    "Wells_DVT": {
        "name": "Wells Score for DVT",
        "description": "Estimates probability of Deep Vein Thrombosis.",
        "applicable_conditions": ["leg swelling", "DVT", "deep vein thrombosis", "calf pain"],
        "scoring_criteria": {
            "Active_cancer": {"0": "No", "1": "Yes (treatment within 6 months or palliative)"},
            "Paralysis_paresis_immobilization": {"0": "No", "1": "Yes"},
            "Bedridden_3_days_or_surgery_within_12_weeks": {"0": "No", "1": "Yes"},
            "Localized_tenderness_along_deep_venous_system": {"0": "No", "1": "Yes"},
            "Entire_leg_swollen": {"0": "No", "1": "Yes"},
            "Calf_swelling_3cm_greater_than_other_side": {"0": "No", "1": "Yes"},
            "Pitting_edema": {"0": "No", "1": "Yes"},
            "Collateral_superficial_veins": {"0": "No", "1": "Yes"},
            "Alternative_diagnosis_as_likely": {"0": "No", "-2": "Yes"},
        },
        "interpretation": {
            "0-1": {"risk": "Low", "probability": "5%", "recommendation": "D-dimer testing; if negative, DVT excluded"},
            "2": {"risk": "Moderate", "probability": "17%", "recommendation": "D-dimer or ultrasound; consider anticoagulation if confirmed"},
            "3+": {"risk": "High", "probability": "53%", "recommendation": "Ultrasound recommended; start anticoagulation if confirmed"},
        },
    },
}


def seed_all():
    """Write all seed data to JSON files."""
    patients_path = os.path.join(DATA_DIR, "patients.json")
    rules_path = os.path.join(DATA_DIR, "clinical_rules.json")

    with open(patients_path, "w") as f:
        json.dump(PATIENTS, f, indent=2)
    print(f"Seeded {len(PATIENTS)} patients -> {patients_path}")

    with open(rules_path, "w") as f:
        json.dump(CLINICAL_RULES, f, indent=2)
    print(f"Seeded {len(CLINICAL_RULES)} clinical rules -> {rules_path}")


if __name__ == "__main__":
    seed_all()