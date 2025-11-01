"""
Plan-driven API test:
- Seeds fake users and an approved TravelPlan into group_chat_agent DB
- Mocks ExpediaAgent to avoid real browser/network
- Calls booking endpoints via FastAPI TestClient
"""

import os
import json
from typing import Any, Dict

# Use a file-based SQLite DB for test isolation
os.environ["DATABASE_URL"] = "sqlite:///./test_group_chat_agent.db"

from group_chat_agent.database import (
    init_db,
    get_session,
    create_user,
    create_session as gc_create_session,
    update_chat_session,
)
from group_chat_agent.models import (
    UserPreferences,
    TravelPlan,
    TravelDates,
    FlightDetails,
    HotelDetails,
    BudgetBreakdown,
    TravelPreferences as PlanPrefs,
)


def seed_fake_users_and_plan() -> str:
    """Create two users and an approved plan; return session_id."""
    # Ensure a clean DB for repeatable tests
    db_path = "test_group_chat_agent.db"
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass
    init_db()
    db = get_session()
    try:
        # Create users
        uids = ["user_a", "user_b"]
        pref_a = UserPreferences(
            budget_range=(1000, 2500),
            preferred_destinations=["beaches"],
            travel_style="adventure",
            dietary_restrictions=[],
            mobility_requirements=[],
            preferred_airlines=["Delta"],
            hotel_amenities=["wifi", "gym"],
        )
        pref_b = UserPreferences(
            budget_range=(1200, 2200),
            preferred_destinations=["cities"],
            travel_style="relaxation",
            dietary_restrictions=["vegetarian"],
            mobility_requirements=[],
            preferred_airlines=["United"],
            hotel_amenities=["wifi"],
        )

        create_user(
            db,
            user_id=uids[0],
            user_name="Alice",
            email="alice@example.com",
            preferences=pref_a.model_dump(),
        )
        create_user(
            db,
            user_id=uids[1],
            user_name="Bob",
            email="bob@example.com",
            preferences=pref_b.model_dump(),
        )

        # Create group chat session
        session_id = "session_test_001"
        gc_create_session(db, session_id=session_id, user_ids=uids, messages_per_agent=3)

        # Build plan
        plan = TravelPlan(
            plan_id="plan_test_001",
            dates=TravelDates(
                departure_date="2025-12-15",
                return_date="2025-12-20",
                flexibility_days=1,
            ),
            flight=FlightDetails(
                origin="LAX",
                destination="JFK",
                preferences="Economy class, prefer nonstop",
                max_budget_per_person=500,
                preferred_departure_time="morning",
            ),
            hotel=HotelDetails(
                location="Manhattan, New York",
                type="hotel",
                amenities=["wifi", "breakfast"],
                star_rating_min=3,
                max_budget_per_night=200,
            ),
            budget=BudgetBreakdown(
                total_per_person=1800,
                flight_cost=500,
                hotel_cost=800,
                activities_cost=300,
                food_cost=200,
            ),
            location="New York City",
            preferences=PlanPrefs(
                activities=["museums", "dining"],
                dining="variety",
                special_requirements=[],
            ),
            compromises_made="Balanced nonstops with hotel rating",
            participants=uids,
            status="approved",
        )

        update_chat_session(
            db,
            session_id=session_id,
            final_plan=plan.model_dump(mode="json"),
            status="approved",
            current_volley=1,
        )

        return session_id
    finally:
        db.close()


class FakeExpediaAgent:
    def __init__(self, llm_model: str = "", proxy_country_code: str = ""):
        self.use_hybrid = True

    # Both booking modes
    def book_parallel(self, **kwargs) -> Dict[str, Any]:
        return {
            "status": "success",
            "message": "Parallel booking simulated",
            "booking_mode": "parallel",
            "results": {"flight": {"ok": True}, "hotel": {"ok": True}},
        }

    def book_flight_and_hotel_package(self, **kwargs) -> Dict[str, Any]:
        return {
            "status": "success",
            "message": "Package booking simulated",
            "booking_mode": "sequential",
            "results": {"package": {"ok": True}},
        }

    # Flight-only chain
    def create_profile(self):
        return "profile"

    def create_session(self, profile_id: str | None = None):
        return "session"

    def login(self, **kwargs):
        return {"status": "success"}

    def search_flights(self, **kwargs):
        return {"status": "success", "search": "flights"}

    def select_and_book_flight(self, **kwargs):
        return {"status": "success", "select": "flight"}

    def fill_traveler_info(self, **kwargs):
        return {"status": "success", "traveler": True}

    def fill_payment_info(self, **kwargs):
        return {"status": "success", "payment": True}

    # Hotel-only chain
    def search_hotels(self, **kwargs):
        return {"status": "success", "search": "hotels"}

    def select_and_book_hotel(self, **kwargs):
        return {"status": "success", "select": "hotel"}

    def cleanup(self):
        return None


def build_payload() -> Dict[str, Any]:
    return {
        "credentials": {"email": "e@example.com", "password": "secret"},
        "traveler": {"first_name": "John", "last_name": "Doe", "phone": "4155551234"},
        "payment": {
            "card_number": "4111111111111111",
            "cardholder_name": "John Doe",
            "expiration_month": "12",
            "expiration_year": "2027",
            "cvv": "123",
            "billing_address": {
                "street": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94102",
                "country": "USA",
            },
        },
        "passengers": 2,
        "parallel_booking": True,
    }


def run_test():
    # Seed DB
    session_id = seed_fake_users_and_plan()

    # Import API app and monkeypatch agent
    import agent_service as svc
    svc.ExpediaAgent = FakeExpediaAgent  # type: ignore

    from fastapi.testclient import TestClient
    client = TestClient(svc.app)

    payload = build_payload()

    # both
    r = client.post(f"/group-chat/{session_id}/book", json=payload)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] == "success"
    assert j.get("booking_mode") in {"parallel", "sequential"}

    # flight-only
    r2 = client.post(f"/group-chat/{session_id}/book/flight", json=payload)
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "success"

    # hotel-only
    r3 = client.post(f"/group-chat/{session_id}/book/hotel", json=payload)
    assert r3.status_code == 200, r3.text
    assert r3.json()["status"] == "success"

    print("All API plan booking tests passed.")


if __name__ == "__main__":
    run_test()


