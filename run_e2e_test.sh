#!/bin/bash

# E2E Test Runner Script
# Runs end-to-end tests for Group Chat → Expedia Booking flow

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║       E2E Test: Group Chat to Expedia Booking Flow            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo ""
    echo "Please create a .env file with the following keys:"
    echo "  - BROWSER_USE_API_KEY (required)"
    echo "  - OPENAI_API_KEY or ANTHROPIC_API_KEY (required)"
    echo "  - AGENTMAIL_API_KEY (optional)"
    echo "  - HYPERSPELL_API_KEY (optional)"
    echo ""
    exit 1
fi

# Check for required API keys
if ! grep -q "BROWSER_USE_API_KEY" .env; then
    echo "⚠️  WARNING: BROWSER_USE_API_KEY not found in .env"
    echo "   Real browser automation will fail without this key"
fi

if ! grep -q "OPENAI_API_KEY\|ANTHROPIC_API_KEY" .env; then
    echo "⚠️  WARNING: No LLM API key found in .env"
    echo "   Group chat deliberations require OpenAI or Anthropic API key"
fi

echo ""
echo "📋 Test Options:"
echo "  1. Run all E2E tests (~15-20 minutes)"
echo "  2. Run test_full_flow_with_approval (~5-8 minutes)"
echo "  3. Run test_rejection_and_new_volley (~8-12 minutes)"
echo "  4. Run test_parallel_booking_execution (~2-5 minutes)"
echo ""

# Check if argument provided
if [ $# -eq 0 ]; then
    read -p "Select test to run [1-4]: " choice
else
    choice=$1
fi

echo ""
echo "🚀 Starting test..."
echo ""

case $choice in
    1)
        echo "Running all E2E tests..."
        python3 -m pytest test_e2e_group_chat_booking.py -v -s
        ;;
    2)
        echo "Running test_full_flow_with_approval..."
        python3 -m pytest test_e2e_group_chat_booking.py::TestE2EGroupChatBooking::test_full_flow_with_approval -v -s
        ;;
    3)
        echo "Running test_rejection_and_new_volley..."
        python3 -m pytest test_e2e_group_chat_booking.py::TestE2EGroupChatBooking::test_rejection_and_new_volley -v -s
        ;;
    4)
        echo "Running test_parallel_booking_execution..."
        python3 -m pytest test_e2e_group_chat_booking.py::TestE2EGroupChatBooking::test_parallel_booking_execution -v -s
        ;;
    *)
        echo "❌ Invalid choice. Please select 1-4."
        exit 1
        ;;
esac

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    Test Completed!                             ║"
echo "╚════════════════════════════════════════════════════════════════╝"

