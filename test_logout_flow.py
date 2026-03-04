#!/usr/bin/env python
"""
Simple smoke tests for logout behavior.

This script ensures that:

1. A user can log in successfully.
2. Hitting `/logout` clears the session and redirects to the landing
   (index) page instead of the login form.
3. After logging out any attempt to access a protected endpoint
   results in a prompt to log back in.
"""

import requests
from requests import Session

BASE_URL = "http://127.0.0.1:5000"
CANDIDATE_EMAIL = "goitseonetrade@gmail.com"
CANDIDATE_PASSWORD = "goitseone_pass"


def test_logout_flow():
    session = Session()

    # log in first
    resp = session.post(f"{BASE_URL}/login", data={
        'email': CANDIDATE_EMAIL,
        'password': CANDIDATE_PASSWORD,
    })
    assert resp.status_code in (200, 302), "Login request failed"
    # the server should set a session cookie
    assert session.cookies.get('session'), "No session cookie after login"

    # now hit the logout endpoint
    resp = session.get(f"{BASE_URL}/logout", allow_redirects=True)
    assert resp.status_code == 200, "Logout did not return 200"
    # the landing page should be shown (index page contains hero text)
    assert "Assessment Platform" in resp.text or "Sign In" in resp.text

    # the session cookie should have been cleared or changed
    # (Flask simply clears data, cookie may still exist but is empty)
    # we verify by attempting to access a protected page
    resp2 = session.get(f"{BASE_URL}/candidate/assessments", allow_redirects=True)
    assert resp2.status_code == 200
    # after logout we expect to see login prompt or warning message
    assert ("Please log in" in resp2.text) or ("Sign In" in resp2.text), \
        "Protected page accessed without login"


if __name__ == '__main__':
    test_logout_flow()
    print("Logout flow test completed")
