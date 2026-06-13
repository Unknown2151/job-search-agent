"""
Standalone test script to verify all job search tools work correctly.
Run:  python search_tools.py
"""
from dotenv import load_dotenv
load_dotenv()

import json
import asyncio
from tools.linkedin_search_tool import search_linkedin_jobs
from tools.naukri_search_tool import search_naukri_jobs
from tools.indeed_search_tool import search_indeed_jobs

if __name__ == "__main__":
    target_role = "Python Developer"
    target_location = "Chennai"

    print("--- STARTING JOB SEARCH ACROSS ALL PLATFORMS ---\n")

    # --- LinkedIn ---
    print("--- Searching LinkedIn... ---")
    linkedin_jobs = asyncio.run(search_linkedin_jobs(f"{target_role}, {target_location}"))
    if isinstance(linkedin_jobs, list) and linkedin_jobs:
        print(json.dumps(linkedin_jobs[:3], indent=2))
    else:
        print(f"LinkedIn result: {linkedin_jobs}")
    print("-" * 30 + "\n")

    # --- Naukri.com ---
    print("--- Searching Naukri.com... ---")
    naukri_jobs = search_naukri_jobs(f"{target_role}, {target_location}")
    if isinstance(naukri_jobs, list) and naukri_jobs:
        print(json.dumps(naukri_jobs[:3], indent=2))
    else:
        print(f"Naukri result: {naukri_jobs}")
    print("-" * 30 + "\n")

    # --- Indeed ---
    print("--- Searching Indeed... ---")
    indeed_jobs = search_indeed_jobs(role=target_role, location=target_location)
    if isinstance(indeed_jobs, list) and indeed_jobs:
        print(json.dumps(indeed_jobs[:3], indent=2))
    else:
        print(f"Indeed result: {indeed_jobs}")
    print("-" * 30 + "\n")

    print("---  JOB SEARCH COMPLETE  ---")