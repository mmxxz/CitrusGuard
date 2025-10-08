import requests
import uuid
import time
import os
from PIL import Image
import io

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8000/api/v1"
USER_EMAIL = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
USER_PASSWORD = "a-secure-password"
PROXIES = {"http": None, "https": None}

def run_test():
    """Runs the comprehensive end-to-end API test workflow."""
    access_token = None
    orchard_id = None
    session_id = None

    try:
        # --- 1. Register User ---
        print(f"--- 1. Registering user {USER_EMAIL} ---")
        response = requests.post(f"{BASE_URL}/users/register", json={"email": USER_EMAIL, "password": USER_PASSWORD, "full_name": "Test User"}, proxies=PROXIES)
        response.raise_for_status()
        print("✅ User registered successfully.")
        
        # --- 2. Login User ---
        print(f"\n--- 2. Logging in user {USER_EMAIL} ---")
        response = requests.post(f"{BASE_URL}/users/login/token", data={"username": USER_EMAIL, "password": USER_PASSWORD}, proxies=PROXIES)
        response.raise_for_status()
        access_token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        print("✅ User logged in successfully.")

        # --- 3. Create Orchard ---
        print("\n--- 3. Creating an orchard ---")
        orchard_payload = {"name": "My Test Orchard", "address_detail": "Test Valley"}
        response = requests.post(f"{BASE_URL}/orchards/", json=orchard_payload, headers=headers, proxies=PROXIES)
        response.raise_for_status()
        orchard_id = response.json()["id"]
        print(f"✅ Orchard created successfully with ID: {orchard_id}")

        # --- 4. List & Verify Orchard ---
        print("\n--- 4. Listing and verifying orchard ---")
        response = requests.get(f"{BASE_URL}/orchards/", headers=headers, proxies=PROXIES)
        response.raise_for_status()
        assert len(response.json()) == 1 and response.json()[0]["id"] == orchard_id
        print("✅ Orchard list verified.")
        
        response = requests.get(f"{BASE_URL}/orchards/{orchard_id}", headers=headers, proxies=PROXIES)
        response.raise_for_status()
        assert response.json()["name"] == "My Test Orchard"
        print("✅ Orchard detail verified.")

        # --- 5. Update Orchard ---
        print("\n--- 5. Updating orchard ---")
        update_payload = {"name": "My Updated Orchard"}
        response = requests.put(f"{BASE_URL}/orchards/{orchard_id}", json=update_payload, headers=headers, proxies=PROXIES)
        response.raise_for_status()
        assert response.json()["name"] == "My Updated Orchard"
        print("✅ Orchard updated successfully.")

        # --- 6. Health & Alerts ---
        print("\n--- 6. Checking health and alerts ---")
        response = requests.get(f"{BASE_URL}/orchards/{orchard_id}/health_overview", headers=headers, proxies=PROXIES)
        response.raise_for_status()
        assert "health_score" in response.json()
        print("✅ Health overview endpoint is working.")
        
        response = requests.get(f"{BASE_URL}/orchards/{orchard_id}/alerts", headers=headers, proxies=PROXIES)
        response.raise_for_status()
        assert isinstance(response.json(), list)
        print("✅ Alerts endpoint is working (returns a list).")

        # --- 7. Upload Image ---
        print("\n--- 7. Uploading an image ---")
        # Create a simple test image using PIL
        img = Image.new('RGB', (100, 100), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        img_buffer.seek(0)
        
        response = requests.post(f"{BASE_URL}/upload/image", 
                               files={"file": ("test_image.jpg", img_buffer, "image/jpeg")}, 
                               proxies=PROXIES)
        response.raise_for_status()
        image_url = response.json()["image_url"]
        assert image_url.startswith("http")
        print(f"✅ Image uploaded successfully: {image_url}")

        # --- 8. Full Diagnosis Flow ---
        print("\n--- 8. Running full diagnosis flow ---")
        response = requests.post(f"{BASE_URL}/orchards/{orchard_id}/diagnosis/start", json={"initial_description": "Yellow leaves"}, headers=headers, proxies=PROXIES)
        response.raise_for_status()
        session_id = response.json()["session_id"]
        print(f"✅ Diagnosis started (Session ID: {session_id}).")

        response = requests.post(f"{BASE_URL}/orchards/{orchard_id}/diagnosis/{session_id}/continue", json={"user_input": "It's on the 老叶"}, headers=headers, proxies=PROXIES)
        response.raise_for_status()
        print("✅ Diagnosis continued, triggering result creation.")
        
        # Wait for the async task to complete (6 steps * 1.5s = 9s + buffer)
        time.sleep(10)

        response = requests.get(f"{BASE_URL}/orchards/{orchard_id}/diagnosis/{session_id}/result", headers=headers, proxies=PROXIES)
        response.raise_for_status()
        assert response.json()["primary_diagnosis"] == "柑橘缺镁症"
        print("✅ Diagnosis result fetched successfully.")

        # --- 9. Cleanup: Delete Orchard ---
        print("\n--- 9. Cleaning up: Deleting orchard ---")
        response = requests.delete(f"{BASE_URL}/orchards/{orchard_id}", headers=headers, proxies=PROXIES)
        response.raise_for_status()
        print("✅ Orchard deleted successfully.")
        
        response = requests.get(f"{BASE_URL}/orchards/{orchard_id}", headers=headers, proxies=PROXIES)
        assert response.status_code == 404
        print("✅ Orchard deletion verified (404 Not Found).")

        print("\n\n🎉🎉🎉 ALL TESTS PASSED! 🎉🎉🎉")

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ TEST FAILED!")
        print(f"Step: {e.request.method} {e.request.url}")
        print(f"Status Code: {e.response.status_code}")
        try:
            print(f"Response: {e.response.json()}")
        except:
            print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ AN UNEXPECTED ERROR OCCURRED: {e}")

if __name__ == "__main__":
    run_test()