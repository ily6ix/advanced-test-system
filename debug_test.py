#!/usr/bin/env python
"""
Debug script to check what the take_assessment endpoint returns
"""

import requests
from requests import Session

BASE_URL = "http://127.0.0.1:5000"
CANDIDATE_EMAIL = "goitseonetrade@gmail.com"
CANDIDATE_PASSWORD = "goitseone_pass"
ASSESSMENT_ID = 1

session = Session()

# Step 1: Login
print("Logging in...")
response = session.post(f"{BASE_URL}/login", data={
    'email': CANDIDATE_EMAIL,
    'password': CANDIDATE_PASSWORD
})
print(f"Login status: {response.status_code}")

# Step 2: Access assessment rules
print(f"\nAccessing assessment rules...")
response = session.get(f"{BASE_URL}/candidate/assessments/{ASSESSMENT_ID}/take")
print(f"Status code: {response.status_code}")
print("\nResponse snippets:")
print("=" * 60)
print(response.text[:1500] if len(response.text) > 1500 else response.text)
print("=" * 60)

# Check for key text
print("\nText checks:")
print(f"Contains 'Important Rules': {'Important Rules' in response.text}")
print(f"Contains 'Start Assessment': {'Start Assessment' in response.text}")
print(f"Contains 'Assessment Progress': {'Assessment Progress' in response.text}")
print(f"Contains 'Take Assessment': {'Take Assessment' in response.text}")
print(f"Contains 'question_item': {'question_item' in response.text}")
print(f"Contains error text: {'not found' in response.text.lower()}")
