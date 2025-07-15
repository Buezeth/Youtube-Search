# test_key.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load the environment variables from your .env file
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("🛑 ERROR: GEMINI_API_KEY not found in .env file.")
else:
    print("✅ API Key found in .env file.")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        print("⏳ Attempting to make a single API call...")
        response = model.generate_content("Hello")
        print("✅ SUCCESS! The API call worked. The key is valid and has a fresh quota.")
        print("First few words of response:", response.text[:50] + "...")
    except Exception as e:
        print("\n🛑 ERROR: The API call failed.")
        print("This likely means the quota is still exhausted, or the API was not enabled for the project.")
        print("\n--- Full Error ---")
        print(e)
        print("------------------")