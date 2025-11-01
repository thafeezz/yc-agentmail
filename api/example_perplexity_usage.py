"""
Example usage of Perplexity travel search tools.

This script demonstrates how to use the Perplexity tools in a real-world scenario.
Make sure to set PERPLEXITY_API_KEY in your .env file before running.

Run with: python api/example_perplexity_usage.py
"""

from perplexity_tools import (
    search_travel_destinations,
    search_multiple_travel_topics,
    search_local_travel_info
)


def example_basic_search():
    """Example 1: Basic travel destination search."""
    print("\n" + "="*80)
    print("Example 1: Basic Travel Destination Search")
    print("="*80)
    
    result = search_travel_destinations.invoke({
        "query": "best time to visit Japan for cherry blossoms",
        "max_results": 5
    })
    
    print(result)


def example_location_specific_search():
    """Example 2: Location-specific search with country filter."""
    print("\n" + "="*80)
    print("Example 2: Location-Specific Search")
    print("="*80)
    
    result = search_travel_destinations.invoke({
        "query": "luxury beach resorts",
        "country": "MV",  # Maldives
        "max_results": 3
    })
    
    print(result)


def example_multi_query_trip_planning():
    """Example 3: Multi-query search for complete trip planning."""
    print("\n" + "="*80)
    print("Example 3: Multi-Query Trip Planning")
    print("="*80)
    
    result = search_multiple_travel_topics.invoke({
        "queries": [
            "affordable hotels in Barcelona near Sagrada Familia",
            "best tapas restaurants in Barcelona",
            "free things to do in Barcelona",
            "Barcelona metro pass for tourists"
        ],
        "max_results": 15
    })
    
    print(result)


def example_local_hidden_gems():
    """Example 4: Find local hidden gems in a specific country."""
    print("\n" + "="*80)
    print("Example 4: Local Hidden Gems")
    print("="*80)
    
    result = search_local_travel_info.invoke({
        "query": "hidden gem restaurants and local food markets",
        "country_code": "TH",  # Thailand
        "max_results": 5
    })
    
    print(result)


def example_travel_safety_and_restrictions():
    """Example 5: Check travel safety and current restrictions."""
    print("\n" + "="*80)
    print("Example 5: Travel Safety and Restrictions")
    print("="*80)
    
    result = search_travel_destinations.invoke({
        "query": "current travel restrictions and safety guidelines for Indonesia 2024",
        "max_results": 5
    })
    
    print(result)


def example_budget_travel():
    """Example 6: Budget travel planning."""
    print("\n" + "="*80)
    print("Example 6: Budget Travel Planning")
    print("="*80)
    
    result = search_multiple_travel_topics.invoke({
        "queries": [
            "cheapest European countries to visit 2024",
            "budget hostels Europe recommendations",
            "free walking tours Europe major cities"
        ],
        "country": "GB",  # Start from UK perspective
        "max_results": 12
    })
    
    print(result)


def example_activity_specific_search():
    """Example 7: Search for specific activities."""
    print("\n" + "="*80)
    print("Example 7: Activity-Specific Search")
    print("="*80)
    
    result = search_local_travel_info.invoke({
        "query": "best hiking trails and mountain treks for beginners",
        "country_code": "NZ",  # New Zealand
        "max_results": 5
    })
    
    print(result)


def example_seasonal_travel():
    """Example 8: Seasonal travel recommendations."""
    print("\n" + "="*80)
    print("Example 8: Seasonal Travel Recommendations")
    print("="*80)
    
    result = search_travel_destinations.invoke({
        "query": "best winter destinations in Europe December Christmas markets",
        "max_results": 8
    })
    
    print(result)


def main():
    """Run all examples."""
    print("\n")
    print("*" * 80)
    print("PERPLEXITY TRAVEL SEARCH TOOLS - EXAMPLES")
    print("*" * 80)
    
    examples = [
        ("Basic Search", example_basic_search),
        ("Location-Specific", example_location_specific_search),
        ("Multi-Query Planning", example_multi_query_trip_planning),
        ("Local Hidden Gems", example_local_hidden_gems),
        ("Travel Safety", example_travel_safety_and_restrictions),
        ("Budget Travel", example_budget_travel),
        ("Activity-Specific", example_activity_specific_search),
        ("Seasonal Travel", example_seasonal_travel)
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nChoose an example to run (1-8), 'all' to run all, or 'q' to quit:")
    choice = input("> ").strip().lower()
    
    if choice == 'q':
        print("Goodbye!")
        return
    
    if choice == 'all':
        for name, func in examples:
            try:
                func()
            except Exception as e:
                print(f"\nError in {name}: {e}")
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(examples):
                name, func = examples[idx]
                func()
            else:
                print("Invalid choice. Please enter a number between 1 and 8.")
        except ValueError:
            print("Invalid input. Please enter a number, 'all', or 'q'.")
    
    print("\n" + "*" * 80)
    print("Examples complete!")
    print("*" * 80 + "\n")


if __name__ == "__main__":
    # Check if Perplexity API key is set
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if not os.getenv("PERPLEXITY_API_KEY"):
        print("\n⚠️  WARNING: PERPLEXITY_API_KEY not found in environment variables!")
        print("Please set it in your .env file to run these examples.\n")
        print("Get your API key from: https://www.perplexity.ai/settings/api\n")
        exit(1)
    
    main()

