"""
Quick diagnostic script to test API connectivity and configuration.
Run this to see what's actually working/broken.
"""
import os
import sys
from dotenv import load_dotenv

print("=" * 60)
print("AI JOB SEARCH AGENT - DIAGNOSTIC TEST")
print("=" * 60)

# Load environment
load_dotenv()

# 1. Check environment variables
print("\n1. CHECKING ENVIRONMENT VARIABLES:")
print("-" * 60)

apis = {
    "GOOGLE_API_KEY": "Google Generative AI (REQUIRED)",
    "SERPAPI_API_KEY": "SerpAPI (REQUIRED)",
    "OPENAI_API_KEY": "OpenAI (optional)",
    "NOTION_API_TOKEN": "Notion (optional)",
}

for api_name, description in apis.items():
    value = os.getenv(api_name, "NOT SET")
    status = "OK" if value != "NOT SET" else "MISSING"
    display = f"{value[:20]}..." if len(str(value)) > 20 else value
    print(f"[{status:7}] {api_name:20} = {display}")

# 2. Check imports
print("\n2. CHECKING CRITICAL IMPORTS:")
print("-" * 60)

imports_to_check = [
    ("streamlit", "Streamlit UI Framework"),
    ("langchain", "LangChain"),
    ("langchain_google_genai", "Google Generative AI"),
    ("langgraph", "LangGraph"),
    ("selenium", "Selenium"),
    ("aiohttp", "AsyncIO HTTP"),
]

for module_name, description in imports_to_check:
    try:
        __import__(module_name)
        print(f"[OK      ] {module_name:25} - {description}")
    except ImportError as e:
        print(f"[FAIL    ] {module_name:25} - {e}")

# 3. Test Google API connection
print("\n3. TESTING GOOGLE API CONNECTION:")
print("-" * 60)

google_key = os.getenv("GOOGLE_API_KEY")
if not google_key:
    print("[MISSING] GOOGLE_API_KEY not set")
else:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        print("[OK      ] Google Generative AI imported")

        try:
            print("[INFO    ] Initializing LLM...")
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                api_key=google_key,
                temperature=0.0,
                timeout=10,
                max_retries=1
            )
            print("[OK      ] LLM initialized")

            # Try a simple test
            print("[INFO    ] Testing LLM with simple query...")
            response = llm.invoke("Say 'Hello' and nothing else.")
            print(f"[OK      ] LLM Response: {response.content[:50]}...")
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"[FAIL    ] LLM test failed")
            print(f"[ERROR   ] {error_msg}")
            print(f"[TIP     ] Check if API key is valid and has quota")
    except Exception as e:
        print(f"[FAIL    ] Import failed: {e}")

# 4. Test SerpAPI connection
print("\n4. TESTING SERPAPI CONNECTION:")
print("-" * 60)

serpapi_key = os.getenv("SERPAPI_API_KEY")
if not serpapi_key:
    print("[MISSING] SERPAPI_API_KEY not set")
else:
    try:
        print("[INFO    ] SerpAPI key is set")
    except Exception as e:
        print(f"[FAIL    ] SerpAPI test failed: {e}")

# 5. Test file parsing
print("\n5. TESTING FILE PARSING:")
print("-" * 60)

try:
    from tools.resume_parser_tool import parse_resume
    print("[OK      ] Resume parser imported")
except Exception as e:
    print(f"[FAIL    ] Resume parser import failed: {e}")

# 6. Test job search tools
print("\n6. TESTING JOB SEARCH TOOLS:")
print("-" * 60)

try:
    from tools.linkedin_search_tool import search_linkedin_jobs
    print("[OK      ] LinkedIn search tool imported")
except Exception as e:
    print(f"[FAIL    ] LinkedIn search import failed: {e}")

try:
    from tools.naukri_search_tool import search_naukri_jobs
    print("[OK      ] Naukri search tool imported")
except Exception as e:
    print(f"[FAIL    ] Naukri search import failed: {e}")

# 7. Summary
print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)

print("\nKEY FINDINGS:")
has_google = bool(os.getenv("GOOGLE_API_KEY"))
has_serpapi = bool(os.getenv("SERPAPI_API_KEY"))

if has_google and has_serpapi:
    print("[INFO] Both required API keys are set")
else:
    print("[WARNING] Missing required API keys:")
    if not has_google:
        print("  - GOOGLE_API_KEY (required for AI features)")
    if not has_serpapi:
        print("  - SERPAPI_API_KEY (required for search)")

print("\nNEXT STEPS:")
print("1. Verify .env file is in project root directory")
print("2. Run: python diagnose.py")
print("3. Check output above for specific issues")
print("4. If LLM test fails, verify API key is active")
print("5. Restart Streamlit app after any changes")
