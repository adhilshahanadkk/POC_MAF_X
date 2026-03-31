import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

project = os.getenv("GOOGLE_CLOUD_PROJECT", "project-fea13377-5812-4bae-9ee")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
api_key = os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=api_key, vertexai=True,
                      project=project, location=location)

print(f"Google GenAI initialized: project={project}, location={location}")
print("Available Gemini models can be used directly:")
print("  - gemini-2.5-flash")
print("  - gemini-2.0-flash")
print("  - gemini-1.5-flash")
print("  - gemini-1.5-pro")