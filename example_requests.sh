#!/bin/bash
# Example API requests for the Expedia Booking Agent

# Base URL
API_URL="http://localhost:8000"

echo "================================================"
echo "Expedia Booking Agent API - Example Requests"
echo "================================================"

# 1. Health Check
echo -e "\n1. Health Check"
echo "---"
curl -X GET "${API_URL}/health" | jq

# 2. Search Flights Only
echo -e "\n2. Search for Flights"
echo "---"
curl -X POST "${API_URL}/search/flights" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "Los Angeles",
    "destination": "New York",
    "departure_date": "2025-12-15",
    "return_date": "2025-12-20",
    "passengers": 1
  }' | jq

# 3. Search Hotels Only
echo -e "\n3. Search for Hotels"
echo "---"
curl -X POST "${API_URL}/search/hotels" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "New York, NY",
    "check_in": "2025-12-15",
    "check_out": "2025-12-20",
    "guests": 1,
    "rooms": 1
  }' | jq

# 4. Complete Booking (Parallel Mode)
echo -e "\n4. Complete Booking - Parallel Mode"
echo "---"
curl -X POST "${API_URL}/book" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password",
    "create_account": false,
    "origin": "Los Angeles",
    "destination": "New York",
    "departure_date": "December 15, 2025",
    "return_date": "December 20, 2025",
    "hotel_location": "New York, NY",
    "check_in": "12/15/2025",
    "check_out": "12/20/2025",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1-555-0123",
    "card_number": "4111111111111111",
    "cardholder_name": "John Doe",
    "expiration_month": "12",
    "expiration_year": "2027",
    "cvv": "123",
    "billing_address": {
      "street": "123 Main St",
      "city": "Los Angeles",
      "state": "CA",
      "zip": "90001",
      "country": "USA"
    },
    "passengers": 1,
    "flight_preference": "cheapest",
    "hotel_preference": "highest rated under $200",
    "parallel_booking": true
  }' | jq

echo -e "\n================================================"
echo "Done! Check the API documentation at:"
echo "${API_URL}/docs"
echo "================================================"

