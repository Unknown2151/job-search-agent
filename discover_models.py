"""
Discover which Google AI models are available for your API key.
This helps identify why the app can't find a suitable model.
"""
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("[ERROR] GOOGLE_API_KEY not found in .env file")
    exit(1)

print("=" * 60)
print("GOOGLE AI MODEL DISCOVERY")
print("=" * 60)

print(f"\nUsing API Key: {GOOGLE_API_KEY[:20]}...")

# Try to use the Google GenerativeAI SDK directly
try:
    import google.generativeai as genai
    genai.configure(api_key=GOOGLE_API_KEY)

    print("\n1. Listing available models:")
    print("-" * 60)

    try:
        models = genai.list_models()
        available_models = []

        for model in models:
            # Filter for generative models (not embeddings, etc)
            if "generateContent" in model.supported_generation_methods:
                available_models.append(model.name)
                print(f"  - {model.name}")

        if not available_models:
            print("  [WARNING] No generative models found!")
            print("  Your API key may not have access to any models yet.")
        else:
            print(f"\n[OK] Found {len(available_models)} available models")

    except Exception as e:
        print(f"[ERROR] Could not list models: {e}")

    print("\n2. Testing available models:")
    print("-" * 60)

    models_to_test = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-pro",
        "gemini-2.0-flash",
    ]

    working_models = []
    for model_name in models_to_test:
        try:
            print(f"  Testing {model_name}...", end=" ")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Test")
            print("[OK]")
            working_models.append(model_name)
        except Exception as e:
            error_msg = str(e)[:50]
            print(f"[FAIL] - {error_msg}")

    print("\n" + "=" * 60)
    if working_models:
        print(f"\nGREAT! These models work with your API key:")
        for model in working_models:
            print(f"  ✓ {model}")
        print("\nThe app should automatically detect and use one of these.")
    else:
        print("\n[WARNING] No working models found!")
        print("\nThis means your GOOGLE_API_KEY may not have access to generative models yet.")
        print("\nSOLUTIONS:")
        print("  1. Check https://ai.google.dev/ - you may need to enable access")
        print("  2. If using free tier, models may take time to be provisioned")
        print("  3. Try creating a new API key")
        print("  4. Ensure the API key has 'AI Studio' access")

except ImportError:
    print("[ERROR] google-generativeai not installed")
    print("Run: pip install google-generativeai")
    exit(1)

except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
    exit(1)

print("\n" + "=" * 60)
