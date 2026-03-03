#!/usr/bin/env python
"""
Comprehensive debug of the assessment system
"""
import json
import sys

print("=" * 60)
print("COMPREHENSIVE ASSESSMENT SYSTEM DEBUG")
print("=" * 60)

# Check 1: Verify assessments.json can be loaded
print("\n[Check 1] Loading assessments.json...")
try:
    with open('data/assessments.json') as f:
        assessments = json.load(f)
    print(f"✓ Loaded {len(assessments)} assessments")
    
    # Check assessment 1
    assessment_1 = next((a for a in assessments if a['id'] == 1), None)
    if assessment_1:
        print(f"  Assessment 1: {assessment_1['title']}")
        print(f"  Status: {assessment_1['results'][0]['status'] if assessment_1.get('results') else 'No results'}")
        if assessment_1.get('results'):
            print(f"  Result status: {assessment_1['results'][0].get('status')}")
except Exception as e:
    print(f"✗ Error loading assessments: {e}")
    sys.exit(1)

# Check 2: Verify users.json can be loaded
print("\n[Check 2] Loading users.json...")
try:
    with open('data/users.json') as f:
        users = json.load(f)
    print(f"✓ Loaded {len(users)} users")
    
    # Find candidate
    candidate = next((u for u in users if u['email'] == 'goitseonetrade@gmail.com'), None)
    if candidate:
        print(f"  Found candidate: {candidate['get_full_name']} (ID: {candidate['id']})")
        print(f"  Active: {candidate['is_active']}")
    else:
        print("  ✗ Candidate not found!")
except Exception as e:
    print(f"✗ Error loading users: {e}")
    sys.exit(1)

# Check 3: Verify Flask app can be imported
print("\n[Check 3] Importing Flask app...")
try:
    import app as flask_app
    print("✓ Flask app imported successfully")
    
    # Check the function logic
    print("  Checking app.get_candidate_assessments()...")
    assessments = flask_app.assessments
    candidate_id = 4
    cand_assessments = flask_app.get_candidate_assessments(candidate_id)
    print(f"  ✓ Found {len(cand_assessments)} assessments for candidate {candidate_id}")
    
    for ca in cand_assessments:
        print(f"    - {ca['assessment']['title']}: {ca['result'].get('status')}")
    
except Exception as e:
    print(f"✗ Error with Flask app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check 4: Test calculate_candidate_stats
print("\n[Check 4] Testing calculate_candidate_stats()...")
try:
    stats = flask_app.calculate_candidate_stats(4)
    print(f"✓ Stats calculated:")
    print(f"  Completed: {stats['completed']}")
    print(f"  Pending: {stats['pending']}")
    print(f"  Average Score: {stats['average_score']}%")
    print(f"  Next Due: {stats['next_due']}")
except Exception as e:
    print(f"✗ Error calculating stats: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)
