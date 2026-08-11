import os
import base64
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def generate_image(prompt):
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            return part.inline_data.data
    return None