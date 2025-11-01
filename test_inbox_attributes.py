#!/usr/bin/env python3
"""
Simple test to inspect AgentMail inbox object attributes
"""
import os
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("AGENT_MAIL_API_KEY") or os.getenv("AGENTMAIL_API_KEY")
if not api_key:
    print("❌ No AgentMail API key found in environment")
    exit(1)

print(f"✅ Found API key: {api_key[:10]}...")

# Initialize AgentMail client
from agentmail import AgentMail

client = AgentMail(api_key=api_key)
print("✅ AgentMail client initialized")

# Create a test inbox
test_client_id = str(uuid.uuid4())
print(f"\n📬 Creating test inbox with client_id: {test_client_id}")

try:
    inbox = client.inboxes.create(client_id=test_client_id)
    
    print("\n" + "="*80)
    print("INBOX OBJECT INSPECTION")
    print("="*80)
    
    print(f"\n1. Type: {type(inbox)}")
    print(f"2. String representation: {inbox}")
    
    print("\n3. All attributes (dir):")
    for attr in dir(inbox):
        if not attr.startswith('_'):
            print(f"   - {attr}")
    
    print("\n4. Trying to access common attributes:")
    attrs_to_check = ['id', 'inbox_id', 'email', 'address', 'uuid', 'client_id']
    for attr in attrs_to_check:
        if hasattr(inbox, attr):
            value = getattr(inbox, attr)
            print(f"   ✅ inbox.{attr} = {value}")
        else:
            print(f"   ❌ inbox.{attr} does not exist")
    
    print("\n5. Object __dict__ (if available):")
    if hasattr(inbox, '__dict__'):
        for key, value in inbox.__dict__.items():
            print(f"   - {key}: {value}")
    
    print("\n6. Using vars():")
    try:
        for key, value in vars(inbox).items():
            print(f"   - {key}: {value}")
    except Exception as e:
        print(f"   ❌ vars() failed: {e}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ Error creating inbox: {e}")
    import traceback
    traceback.print_exc()

