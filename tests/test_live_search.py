"""
Test script to simulate a live job search and track where the Notion save happens.
Run this to debug the search → extraction → Notion save workflow.
"""

import os
import json
import logging
import sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s [%(name)s]: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

load_dotenv()

print("\n" + "="*70)
print("LIVE JOB SEARCH TEST - With Notion Save Tracking")
print("="*70 + "\n")

print("[STEP 1] Initializing Job Agent...")
try:
    from agents.job_agent import create_job_agent, SEARCH_ANALYTICS_DATA
    agent = create_job_agent()
    print("   OK - Agent created successfully\n")
except Exception as e:
    print(f"   [ERROR] Failed to create agent: {e}")
    sys.exit(1)

search_query = "Data Science Internships, Mumbai"
print(f"[STEP 2] Searching for: '{search_query}'")
print("   (Looking for jobs to extract and save)\n")

print("[STEP 3] Running agent.invoke()...\n")
print("-" * 70)

try:
    messages = [HumanMessage(content=f"Find the best {search_query} with remote options. Show me 3-5 opportunities.")]
    
    result = agent.invoke({"messages": messages})
    
    print("-" * 70)
    print("\n[STEP 4] Agent Response Received\n")
    
    # Step 5: Parse the response
    if isinstance(result, dict) and "messages" in result:
        messages_list = result["messages"]
        if messages_list:
            last_message = messages_list[-1]
            
            if hasattr(last_message, 'content'):
                response_text = last_message.content
            elif isinstance(last_message, dict) and "content" in last_message:
                response_text = last_message["content"]
            else:
                response_text = str(last_message)
            
            if isinstance(response_text, list):
                text_parts = []
                for block in response_text:
                    if isinstance(block, dict) and 'text' in block:
                        text_parts.append(block['text'])
                    elif isinstance(block, str):
                        text_parts.append(block)
                response_text = '\n'.join(text_parts)
            
            print("AGENT RESPONSE:")
            print("-" * 70)
            print(response_text)
            print("-" * 70 + "\n")
            
            print("[STEP 5] Extracting Job Data from Response...\n")
            
            import re
            jobs = []
            lines = response_text.split('\n')
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if re.match(r'^\d+\.\s+', line):
                    match = re.match(r'^\d+\.\s+(.+?)\s+at\s+(.+?)\s*(?:-|$)', line)
                    if match:
                        title = match.group(1).strip()
                        company = match.group(2).strip()
                        url = ""
                        
                        for j in range(i + 1, min(i + 5, len(lines))):
                            url_match = re.search(r'(https?://[^\s\)]+)', lines[j])
                            if url_match:
                                url = url_match.group(1).strip()
                                break
                        
                        if url:
                            jobs.append({
                                "title": title,
                                "company": company,
                                "url": url
                            })
                            print(f"   [OK] Found job: {title} at {company}")
                            print(f"      URL: {url}\n")
                
                i += 1
            
            if jobs:
                print(f"\n[STEP 6] Extracted {len(jobs)} jobs total\n")
                
                print("[STEP 7] Attempting to Save to Notion...\n")
                
                from tools.application_tracker_tool import save_jobs_to_notion
                
                jobs_json = json.dumps(jobs)
                result = save_jobs_to_notion(jobs_json)
                
                print(f"   Result: {result}\n")
                
                if "Successfully saved" in result or "Saved" in result:
                    print("   [OK] Jobs saved successfully to Notion!")
                else:
                    print("   [INFO] Check if jobs appear in your Notion 'Job Tracker' database")
            else:
                print("   [ERROR] No jobs could be extracted from the agent response")
                print("   This might mean:")
                print("      • Agent didn't return job listings in expected format")
                print("      • URL extraction failed")
                print("      • Response format is different than expected")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print("\n[CHECK] Now verify your Notion 'Job Tracker' database to see if jobs appear\n")
    
except Exception as e:
    print(f"\n[ERROR] Test failed with error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
