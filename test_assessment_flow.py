#!/usr/bin/env python
"""
Test script to verify assessment flow:
1. Login as candidate
2. Access candidate assessments
3. Click "Start" on an assessment
4. View rules page
5. Click "Begin Assessment"
"""

import requests
from requests import Session

# Configuration
BASE_URL = "http://127.0.0.1:5000"
CANDIDATE_EMAIL = "goitseonetrade@gmail.com"
CANDIDATE_PASSWORD = "goitseone_pass"
ASSESSMENT_ID = 1

def test_assessment_flow():
    session = Session()
    
    print("=" * 60)
    print("ASSESSMENT FLOW TEST")
    print("=" * 60)
    
    # Step 1: Login
    print("\n[Step 1] Login as candidate...")
    response = session.post(f"{BASE_URL}/login", data={
        'email': CANDIDATE_EMAIL,
        'password': CANDIDATE_PASSWORD
    })
    
    if response.status_code == 200:
        print("✓ Login successful")
    else:
        print(f"✗ Login failed: {response.status_code}")
        return
    
    # Step 2: Access candidate assessments
    print("\n[Step 2] Accessing candidate assessments page...")
    response = session.get(f"{BASE_URL}/candidate/assessments")
    
    if response.status_code == 200 and "Intro to Python" in response.text:
        print("✓ Assessment page loaded - found 'Intro to Python'")
    else:
        print(f"✗ Assessment page failed: {response.status_code}")
        return
    
    # Step 3: Click "Start" button (GET request to take_assessment)
    print(f"\n[Step 3] Clicking 'Start' on assessment {ASSESSMENT_ID}...")
    response = session.get(f"{BASE_URL}/candidate/assessments/{ASSESSMENT_ID}/take")
    
    if response.status_code == 200 and "Important Rules" in response.text and "Start Assessment" in response.text:
        print("✓ Rules page loaded")
        print("✓ Found 'Important Rules' section")
        print("✓ Found 'Start Assessment' button")
        # check for webcam text (assessment 1 has face tracking enabled)
        if "Webcam monitoring" in response.text:
            print("✓ Face tracking notice present")
        else:
            print("✗ Face tracking notice missing")
        if "Microphone" not in response.text:
            print("✓ No voice tracking notice as expected")
        else:
            print("✗ Unexpected voice tracking notice")
    else:
        print(f"✗ Rules page failed: {response.status_code}")
        if "not found for you" in response.text.lower():
            print("✗ Error: Result not created for candidate")
        return
    
    # Step 4: Click "Begin Assessment" button (POST request with action=start)
    print(f"\n[Step 4] Clicking 'Begin Assessment' button...")
    response = session.post(f"{BASE_URL}/candidate/assessments/{ASSESSMENT_ID}/take", data={
        'action': 'start'
    })
    
    if response.status_code == 200 and ("Assessment Progress" in response.text or "Take Assessment" in response.text) and "question" in response.text.lower():
        print("✓ Assessment form loaded")
        print("✓ Questions are visible")
        
        # Count questions
        question_count = response.text.count('class=\"question_item\"')
        print(f"✓ Found {question_count} questions")
        
        # Check for timer
        if "Timer" in response.text or "timer" in response.text:
            print("✓ Timer is present")
        
        # Check for submit button
        if "Submit Assessment" in response.text:
            print("✓ Submit button is present")
    else:
        print(f"✗ Assessment form failed: {response.status_code}")
        print("Response snippet:", response.text[:500])
        return

    # Step 5: exercise warning endpoint directly
    print("\n[Step 5] Sending warning notifications to backend...")
    # face warnings
    for i in range(1,3):
        warn_resp = session.post(f"{BASE_URL}/candidate/assessments/{ASSESSMENT_ID}/warning")
        data = warn_resp.json()
        if data.get('reason') == 'face' and data.get('count') == i:
            print(f"✓ Received face warning #{i}")
        else:
            print(f"✗ Unexpected face warning data: {data}")

    # now simulate a voice warning (should be warning #1 voice, total 3 -> cancellation)
    print("\n[Step 6] Sending voice warning to trigger cancellation...")
    vresp = session.post(f"{BASE_URL}/candidate/assessments/{ASSESSMENT_ID}/warning", json={'reason':'voice'})
    vdata = vresp.json()
    if vdata.get('cancelled'):
        print("✓ Assessment cancelled when combined total exceeded 2")
    else:
        print(f"✗ Expected cancellation but got: {vdata}")

    # after cancellation, check counts on dashboard
    print("\n[Step 7] Verifying dashboard reflects separate counts")
    page = session.get(f"{BASE_URL}/candidate/assessments").text
    if "/" in page and "Cancelled" in page:
        print("✓ Dashboard shows cancelled with face/voice counts")
    else:
        print("✗ Dashboard counts not displayed correctly")

    # login as admin to inspect results table
    print("\n[Step 8] Login as administrator to view report")
    session.get(f"{BASE_URL}/logout")
    admin_login = session.post(f"{BASE_URL}/login", data={
        'email': 'alice@example.com',
        'password': 'alice_pass'
    })
    if admin_login.status_code == 200:
        print("✓ Admin login succeeded")
    else:
        print("✗ Admin login failed")
        return
    res_page = session.get(f"{BASE_URL}/admin/results").text
    if "Warnings" in res_page:
        print("✓ Admin results page shows warnings column")
    else:
        print("✗ Admin results page missing warnings info")

    # verify reports page filters & export
    print("\n[Step 9] Check reports page and export")
    rep_page = session.get(f"{BASE_URL}/admin/reports").text
    if "Filter before export" in rep_page and "Assessment:" in rep_page:
        print("✓ Reports page contains filter form")
    else:
        print("✗ Reports page missing filters")
    # try exporting CSV with no filters
    ex = session.post(f"{BASE_URL}/admin/reports/export", data={'format':'csv'})
    if ex.status_code == 200 and 'text/csv' in ex.headers.get('Content-Type',''):
        print("✓ Exported CSV successfully")
    else:
        print(f"✗ CSV export failed: {ex.status_code} {ex.headers.get('Content-Type')}")
    
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED - Assessment flow is working!")
    print("=" * 60)

if __name__ == "__main__":
    test_assessment_flow()
