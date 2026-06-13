"""
Diagnostic script to test Notion API connection and database setup.
Run this to verify your Notion integration is working before using the agent.
"""

import os
import json
import logging
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_notion_connection():
    """Test the Notion API connection step by step."""
    
    print("\n" + "="*60)
    print("NOTION CONNECTION DIAGNOSTIC")
    print("="*60 + "\n")
    
    print("1️Checking NOTION_API_TOKEN...")
    notion_token = os.getenv("NOTION_API_TOKEN")
    if not notion_token:
        print("   NOTION_API_TOKEN is NOT set in .env file")
        print("   TO FIX:")
        print("      → Go to notion.so → Settings & members → Integrations")
        print("      → Create new integration or copy existing token")
        print("      → Add to .env: NOTION_API_TOKEN=secret_xxxxx...")
        return False
    else:
        print("   NOTION_API_TOKEN found")
        print(f"      Token starts with: {notion_token[:20]}...")
    
    print("\n2️Checking NOTION_DATABASE_ID...")
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not database_id:
        print("   NOTION_DATABASE_ID is NOT set in .env file")
        print("   TO FIX:")
        print("      → Open your Notion Job Tracker database")
        print("      → Copy the DATABASE_ID from the URL:")
        print("         https://notion.so/...?v=DATABASE_ID_GOES_HERE")
        print("      → Add to .env: NOTION_DATABASE_ID=your_id_here")
        return False
    else:
        print("   NOTION_DATABASE_ID found")
        print(f"      Database ID: {database_id}")
        
        clean_id = database_id.replace("-", "")
        print(f"      Cleaned ID: {clean_id}")
    
    print("\n3️Attempting to connect to Notion API...")
    try:
        notion = Client(auth=notion_token)
        print("   Successfully authenticated to Notion!")
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        return False
    
    print("\n4️Testing database access...")
    try:
        clean_id = database_id.replace("-", "")
        api_db = notion.databases.retrieve(clean_id)
        print("   Successfully retrieved database!")
        print(f"      Database name: {api_db.get('title', 'Unknown')}")
    except Exception as e:
        print(f"   Could not access database: {e}")
        print("   Make sure:")
        print("      → Database ID is correct (no extra characters)")
        print("      → Notion integration has database access permissions")
        print("      → Database exists and is shared with the integration")
        return False
    
    print("\n5️hecking database fields...")
    try:
        properties = api_db.get('properties', {})
        print(f"   Found {len(properties)} fields in database:")
        for field_name in properties.keys():
            print(f"      • {field_name}")
        
        required_fields = ['Name', 'URL', 'Status']
        has_all_fields = all(field in properties for field in required_fields)
        
        if has_all_fields:
            print("\n   All required fields present (Name, URL, Status)")
        else:
            missing = [f for f in required_fields if f not in properties]
            print(f"\n   Missing fields: {missing}")
            print("   TO FIX: Add these fields to your Notion database manually")
        
    except Exception as e:
        print(f"   Could not read database schema: {e}")
        return False
    
    print("\n6️Attempting a test save...")
    try:
        test_job = {
            "title": "Test Position ",
            "company": "Test Company",
            "url": "https://example.com"
        }
        
        clean_id = database_id.replace("-", "")
        response = notion.pages.create(
            parent={"database_id": clean_id},
            properties={
                "Name": {"title": [{"text": {"content": f"{test_job['title']} at {test_job['company']}"}}]},
                "URL": {"url": test_job['url']},
                "Status": {"select": {"name": "Saved"}}
            }
        )
        
        print("   Test save successful!")
        print(f"      Page ID: {response['id']}")
        print("\n   You can now delete this test entry from Notion if you want")
        
    except Exception as e:
        print(f"   Test save failed: {e}")
        print("   This might be due to:")
        print("      → Invalid Status field options (must have 'Saved' option)")
        print("      → Database permissions issue")
        print("      → Property names not matching exactly")
        return False
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED - Your Notion integration is working!")
    print("="*60 + "\n")
    return True


if __name__ == "__main__":
    success = test_notion_connection()
    exit(0 if success else 1)
