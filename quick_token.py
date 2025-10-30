#!/usr/bin/env python3
"""
Quick Token Generator for Testing
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

def get_token():
    """Get JWT token for testing"""
    url = "https://yfaiauooxwvekdimfeuu.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlmYWlhdW9veHd2ZWtkaW1mZXV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE1OTEyMDksImV4cCI6MjA2NzE2NzIwOX0.rAc49wpyOERCcNpxpI12TPn6NSSoySToNq33bhakEho"
    
    #production
    # url = "https://otobfhnqafoyqinjenle.supabase.co"
    # key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90b2JmaG5xYWZveXFpbmplbmxlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgxMjQwMDYsImV4cCI6MjA3MzcwMDAwNn0.tDZjL1M6JJLEgaycQ_1VsNO07O625FlddwsD3FAD_MM"
    if not url or not key:
        print("❌ Error: Missing Supabase environment variables")
        return None
    
    supabase = create_client(url, key)
    
    # Test credentials (replace with your actual credentials)
    # email = "arunyuvraj1998@gmail.com"  # Replace with your email
    # password = "Arun@123"   # Replace with your password

    # Test credentials (replace with your actual credentials)
    # email = "arun.varadharajalu@infiniai.tech"  # Replace with your email
    # password = "Arun@123"   # Replace with your password

    # Test credentials (replace with your actual credentials) - super user
    email = "superadmin@dil.com"  # Replace with your email
    password = "DilSuperAdmin@2025"   # Replace with your password
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user and response.session:
            print("✅ Token generated successfully!")
            print(f"👤 User ID: {response.user.id}")
            print(f"🔑 Token: {response.session.access_token}")
            print(f"📋 For Swagger UI: Bearer {response.session.access_token}")
            return response.session.access_token
        else:
            print("❌ Login failed")
            return None
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

if __name__ == "__main__":
    token = get_token()
    if token:
        print("\n🎉 Copy the token above and use it in Swagger UI!") 