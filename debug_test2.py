#!/usr/bin/env python
"""
Debug script to check what the take_assessment endpoint returns - full response
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

# Find where the body starts
import re

# Get the actual content after the body tag
body_match = re.search(r'<body>', response.text, re.IGNORECASE)
if body_match:
    body_content = response.text[body_match.start():]
    # Get first 2000 chars of body
    print("\nBody content (first 2000 chars):")
    print("=" * 60)
    print(body_content[:2000])
    print("=" * 60)
    
    # Check for specific sections
    print("\nSection checks:")
    print(f"Contains 'section class=\"section\"': {'section class=\"section\"' in body_content}")
    print(f"Contains 'question_item': {'question_item' in body_content}")
    print(f"Contains 'Important Rules': {'Important Rules' in body_content}") 
    print(f"Contains 'Start Assessment': {'Start Assessment' in body_content}")
    print(f"Contains 'Assessment Details': {'Assessment Details' in body_content}")
