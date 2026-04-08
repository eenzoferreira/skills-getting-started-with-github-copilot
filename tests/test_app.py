"""
Comprehensive tests for the Mergington High School API using FastAPI TestClient.
Tests follow the AAA (Arrange-Act-Assert) pattern and cover all endpoints.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities

@pytest.fixture
def client():
    """Provide TestClient instance for all tests."""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test."""
    # Save original state
    original_activities = {
        key: {
            **value,
            "participants": value["participants"].copy()
        }
        for key, value in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for key in activities:
        activities[key]["participants"] = original_activities[key]["participants"].copy()


class TestRootEndpoint:
    """Tests for GET / endpoint."""
    
    def test_root_redirects_to_static(self, client):
        """
        AAA: Arrange-Act-Assert
        Root endpoint should redirect to /static/index.html (status 307).
        """
        # Arrange - TestClient is ready
        
        # Act - Make GET request to root
        response = client.get("/", follow_redirects=False)
        
        # Assert - Verify redirect
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"
    
    def test_root_follows_redirect(self, client):
        """Root endpoint redirect can be followed."""
        # Arrange - TestClient ready
        
        # Act - Follow redirect
        response = client.get("/", follow_redirects=True)
        
        # Assert - We get static HTML
        assert response.status_code == 200


class TestActivitiesEndpoint:
    """Tests for GET /activities endpoint."""
    
    def test_get_all_activities_success(self, client, reset_activities):
        """Activities endpoint returns all activities with correct structure."""
        # Arrange - Activities database is populated
        
        # Act - Fetch all activities
        response = client.get("/activities")
        
        # Assert - Response is successful and contains expected data
        assert response.status_code == 200
        data = response.json()
        
        # Verify we have all activities
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Art Club" in data
    
    def test_activity_structure(self, client, reset_activities):
        """Each activity has required fields."""
        # Arrange - Activities ready
        
        # Act - Get activities
        response = client.get("/activities")
        data = response.json()
        
        # Assert - Verify structure of first activity
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
    
    def test_get_activities_contains_participants(self, client, reset_activities):
        """Activities list includes enrolled participants."""
        # Arrange - Activities are pre-populated
        
        # Act - Retrieve activities
        response = client.get("/activities")
        data = response.json()
        
        # Assert - Verify participants are listed
        chess_club = data["Chess Club"]
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint."""
    
    def test_signup_success(self, client, reset_activities):
        """Successfully sign up a new student for an activity."""
        # Arrange - Student not yet signed up
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"
        
        # Act - Attempt signup
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert - Signup successful
        assert response.status_code == 200
        data = response.json()
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify student was actually added
        assert email in activities[activity_name]["participants"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Signup fails when activity doesn't exist."""
        # Arrange - Invalid activity name
        activity_name = "Nonexistent Activity"
        email = "student@mergington.edu"
        
        # Act - Attempt signup for non-existent activity
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert - Returns 404 Not Found
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_student(self, client, reset_activities):
        """Signup fails when student already enrolled."""
        # Arrange - Student already in Chess Club
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already enrolled
        
        # Act - Attempt duplicate signup
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert - Returns 400 Bad Request
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_multiple_students_same_activity(self, client, reset_activities):
        """Multiple different students can sign up for same activity."""
        # Arrange - Two different students
        activity_name = "Science Club"
        email1 = "student1@mergington.edu"
        email2 = "student2@mergington.edu"
        initial_count = len(activities[activity_name]["participants"])
        
        # Act - Sign up first student
        response1 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email1}
        )
        
        # Act - Sign up second student
        response2 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email2}
        )
        
        # Assert - Both signups successful
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert len(activities[activity_name]["participants"]) == initial_count + 2
        assert email1 in activities[activity_name]["participants"]
        assert email2 in activities[activity_name]["participants"]
    
    def test_signup_response_format(self, client, reset_activities):
        """Signup response has correct message format."""
        # Arrange - Prepare signup
        activity_name = "Basketball Team"
        email = "player@mergington.edu"
        
        # Act - Sign up
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert - Response has message field
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Signed up" in data["message"]


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/signup endpoint."""
    
    def test_unregister_success(self, client, reset_activities):
        """Successfully unregister an enrolled student."""
        # Arrange - Student is enrolled
        activity_name = "Chess Club"
        email = "michael@mergington.edu"
        initial_count = len(activities[activity_name]["participants"])
        
        # Act - Unregister the student
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert - Unregister successful
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        
        # Verify student was actually removed
        assert email not in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count - 1
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Unregister fails when activity doesn't exist."""
        # Arrange - Invalid activity name
        activity_name = "Nonexistent Activity"
        email = "student@mergington.edu"
        
        # Act - Attempt unregister from non-existent activity
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert - Returns 404 Not Found
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_nonexistent_participant(self, client, reset_activities):
        """Unregister fails when student not enrolled."""
        # Arrange - Student not in Basketball Team
        activity_name = "Basketball Team"
        email = "notstudent@mergington.edu"
        
        # Act - Attempt unregister for non-enrolled student
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert - Returns 404 Not Found
        assert response.status_code == 404
        data = response.json()
        assert "Participant not found" in data["detail"]
    
    def test_unregister_then_signup_again(self, client, reset_activities):
        """Student can re-enroll after unregistering."""
        # Arrange - Student enrolled
        activity_name = "Drama Club"
        email = "newcomer@mergington.edu"
        
        # Act - Sign up first
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Act - Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert unregister_response.status_code == 200
        assert email not in activities[activity_name]["participants"]
        
        # Act - Re-enroll
        reconnect_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert - Re-enrollment successful
        assert reconnect_response.status_code == 200
        assert email in activities[activity_name]["participants"]
    
    def test_unregister_response_format(self, client, reset_activities):
        """Unregister response has correct message format."""
        # Arrange - Student to unregister
        activity_name = "Track and Field"
        email = "alex@mergington.edu"
        
        # Act - Unregister
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert - Response has correct format
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]


class TestEdgeCases:
    """Tests for edge cases and integration scenarios."""
    
    def test_signup_and_verify_in_getactivities(self, client, reset_activities):
        """Newly signed up student appears in /activities endpoint."""
        # Arrange - New student
        activity_name = "Debate Team"
        email = "debater@mergington.edu"
        
        # Act - Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Act - Fetch activities
        activities_response = client.get("/activities")
        
        # Assert - Student appears in the activities list
        assert signup_response.status_code == 200
        assert activities_response.status_code == 200
        
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
    
    def test_case_sensitive_activity_names(self, client, reset_activities):
        """Activity names are case-sensitive."""
        # Arrange - Wrong case for activity name
        email = "student@mergington.edu"
        
        # Act - Try uppercase variant
        response = client.post(
            "/activities/chess club/signup",  # lowercase, should not match "Chess Club"
            params={"email": email}
        )
        
        # Assert - Should fail because case doesn't match
        assert response.status_code == 404
    
    def test_email_case_sensitivity_in_participants(self, client, reset_activities):
        """Email addresses are treated with case sensitivity in participant list."""
        # Arrange - Email variations
        activity_name = "Art Club"
        email_lower = "artist@mergington.edu"
        
        # Act - Sign up with lowercase
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email_lower}
        )
        
        # Assert - Signup succeeds
        assert response.status_code == 200
        assert email_lower in activities[activity_name]["participants"]