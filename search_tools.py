import json
from tools.linkedin_search_tool import search_linkedin_jobs
from tools.naukri_search_tool import search_naukri_jobs
from tools.indeed_search_tool import search_indeed_jobs

if __name__ == "__main__":
    target_role = "Python Developer"
    target_location = "Chennai"

    print("--- STARTING JOB SEARCH ACROSS ALL PLATFORMS ---\n")

    # --- LinkedIn ---
    print("--- Searching LinkedIn... ---")
    linkedin_jobs = search_linkedin_jobs(role=target_role, location=target_location)
    if linkedin_jobs:
        print(json.dumps(linkedin_jobs[:3], indent=2)) # Print first 3 results
    print("-" * 30 + "\n")

    # --- Naukri.com ---
    print("--- Searching Naukri.com... ---")
    naukri_jobs = search_naukri_jobs(role=target_role, location=target_location)
    if naukri_jobs:
        print(json.dumps(naukri_jobs[:3], indent=2))
    print("-" * 30 + "\n")

    # --- Indeed ---
    print("--- Searching Indeed... ---")
    indeed_jobs = search_indeed_jobs(role=target_role, location=target_location)
    if indeed_jobs:
        print(json.dumps(indeed_jobs[:3], indent=2))
    print("-" * 30 + "\n")

    print("---  JOB SEARCH COMPLETE  ---")