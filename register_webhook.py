"""
Manually register AgentMail webhook.
Run this if you need to register or update the webhook URL.
"""

import os
from agentmail import AgentMail
from dotenv import load_dotenv

load_dotenv()

# Initialize AgentMail client
api_key = os.getenv("AGENTMAIL_API_KEY") or os.getenv("AGENT_MAIL_API_KEY")
if not api_key:
    print("❌ Error: AGENTMAIL_API_KEY or AGENT_MAIL_API_KEY not found in .env")
    exit(1)

client = AgentMail(api_key=api_key)

# Webhook URL
webhook_url = "https://43b4d3f07d28.ngrok-free.app/webhooks/agentmail"

print(f"\n🔗 Registering webhook: {webhook_url}")
print("=" * 80)

try:
    # List existing webhooks first
    print("\n📋 Checking existing webhooks...")
    webhooks = client.webhooks.list()
    
    if hasattr(webhooks, 'webhooks'):
        existing = [w for w in webhooks.webhooks if w.url == webhook_url]
        if existing:
            print(f"✅ Webhook already exists!")
            for wh in existing:
                print(f"   ID: {wh.id}")
                print(f"   URL: {wh.url}")
                print(f"   Events: {wh.events if hasattr(wh, 'events') else 'N/A'}")
            print("\n✨ No action needed - webhook is already registered")
            exit(0)
    
    # Register new webhook
    print(f"\n🆕 Creating new webhook...")
    webhook = client.webhooks.create(
        url=webhook_url,
        events=["message.received"]
    )
    
    print(f"\n✅ Webhook registered successfully!")
    print(f"   ID: {webhook.id}")
    print(f"   URL: {webhook.url}")
    print(f"   Events: {webhook.events if hasattr(webhook, 'events') else ['message.received']}")
    print("\n" + "=" * 80)
    print("🎉 AgentMail will now send events to your webhook URL")
    
except Exception as e:
    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
        print(f"\n✅ Webhook already registered (duplicate detected)")
        print(f"   URL: {webhook_url}")
    else:
        print(f"\n❌ Error registering webhook: {e}")
        print(f"   Error type: {type(e).__name__}")
        exit(1)

