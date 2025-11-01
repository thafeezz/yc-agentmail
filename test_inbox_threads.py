#!/usr/bin/env python3
"""
Test to see what inbox.threads.list() returns
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
    inbox_email = inbox.inbox_id
    
    print(f"✅ Created inbox: {inbox_email}")
    print(f"   client_id: {inbox.client_id}")
    
    # Now try to list threads
    print(f"\n📋 Listing threads from inbox: {inbox_email}")
    
    threads = client.inboxes.threads.list(inbox_id=inbox_email)
    
    print(f"\n📊 Threads result:")
    print(f"   Type: {type(threads)}")
    print(f"   Length: {len(threads) if hasattr(threads, '__len__') else 'N/A'}")
    print(f"   Dir: {[attr for attr in dir(threads) if not attr.startswith('_')]}")
    
    # Check common attributes
    for attr in ['data', 'threads', 'items', 'results', 'count']:
        if hasattr(threads, attr):
            value = getattr(threads, attr)
            print(f"   - threads.{attr}: {value} (type: {type(value)})")
    
    # Try to access data attribute if it exists
    thread_list = None
    if hasattr(threads, 'data'):
        thread_list = threads.data
    elif hasattr(threads, 'threads'):
        thread_list = threads.threads
    elif hasattr(threads, 'items'):
        thread_list = threads.items
    
    if thread_list and len(thread_list) > 0:
        print(f"\n🔍 First thread inspection:")
        first_thread = thread_list[0]
        
        if first_thread:
            print(f"   Type: {type(first_thread)}")
            print(f"   Representation: {first_thread}")
            
            # Check attributes
            print(f"\n   Attributes:")
            for attr in ['id', 'thread_id', 'inbox_id']:
                if hasattr(first_thread, attr):
                    value = getattr(first_thread, attr)
                    print(f"     - {attr}: {value} (type: {type(value)})")
                else:
                    print(f"     - {attr}: NOT FOUND")
            
            # Print all attributes
            print(f"\n   All attributes (dir):")
            for attr in dir(first_thread):
                if not attr.startswith('_'):
                    try:
                        value = getattr(first_thread, attr)
                        if not callable(value):
                            print(f"     - {attr}: {value}")
                    except:
                        pass
    else:
        print("   ℹ️  No threads found (inbox is empty)")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

