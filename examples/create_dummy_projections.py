#!/usr/bin/env python3
"""
Create dummy projection data for players in a Yahoo DFS contest.

This script fetches real players from a contest and generates realistic
projection data to demonstrate the projection consensus system.
"""

import asyncio
import csv
import random
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_collection import YahooDFSCollector, SportType


async def main():
    """Create dummy projection data for contest players."""
    
    # Initialize Yahoo collector
    yahoo_collector = YahooDFSCollector()
    
    print("🔍 Fetching Yahoo DFS contest and players...")
    
    # Get a contest and its players
    contests = await yahoo_collector.collect_contests(SportType.NFL, multi_entry_only=True)
    if not contests:
        print("❌ No contests found")
        return
    
    contest = contests[0]  # Use first contest
    print(f"📊 Using contest: {contest.contest_name}")
    
    # Get players for this contest
    yahoo_players = await yahoo_collector.get_standardized_players(contest.contest_id)
    print(f"👥 Found {len(yahoo_players)} players in contest")
    
    # Generate dummy projections for different sources
    print("\n📈 Generating dummy projections...")
    
    # Create dummy projection data
    dummy_projections = []
    
    # Sample projection sources
    sources = ["dailyfantasyfuel", "rotowire", "yahoo", "fantasypros", "numberfire"]
    
    # Generate projections for each player
    for yahoo_name, player_data in yahoo_players.items():
        # Get player info
        position = player_data.get("Position", "QB")
        salary = player_data.get("Salary", 0)
        fppg = player_data.get("FPPG", 0)
        
        # Generate realistic projections based on position and salary
        base_projection = _generate_base_projection(position, salary, fppg)
        
        # Create projections for each source with some variation
        for source in sources:
            # Add realistic variation (±15% from base)
            variation = random.uniform(0.85, 1.15)
            projection = base_projection * variation
            
            # Round to 1 decimal place
            projection = round(projection, 1)
            
            # Add some confidence rating
            confidence = random.uniform(0.6, 0.95)
            confidence = round(confidence, 2)
            
            dummy_projections.append({
                "player_name": yahoo_name,
                "source": source,
                "projection": projection,
                "confidence": confidence,
                "position": position,
                "salary": salary,
                "fppg": fppg,
                "team": player_data.get("Team", ""),
                "opponent": player_data.get("Opponent", ""),
                "game_time": player_data.get("Time", ""),
            })
    
    # Save to CSV
    output_file = Path(__file__).parent / "dummy_projections.csv"
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            "player_name", "source", "projection", "confidence", 
            "position", "salary", "fppg", "team", "opponent", "game_time"
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for projection in dummy_projections:
            writer.writerow(projection)
    
    print(f"✅ Saved {len(dummy_projections)} dummy projections to {output_file}")
    print(f"📊 Generated projections for {len(yahoo_players)} players across {len(sources)} sources")
    
    # Show sample projections
    print("\n🔍 Sample projections:")
    sample_players = list(yahoo_players.keys())[:3]
    for player_name in sample_players:
        player_projections = [p for p in dummy_projections if p["player_name"] == player_name]
        print(f"\n{player_name.title()}:")
        for proj in player_projections[:3]:  # Show first 3 sources
            print(f"  {proj['source']}: {proj['projection']:.1f} (conf: {proj['confidence']:.2f})")


def _generate_base_projection(position: str, salary: int, fppg: float) -> float:
    """Generate realistic base projection based on position, salary, and FPPG."""
    
    # Use FPPG if available, otherwise estimate based on salary
    if fppg and fppg > 0:
        base = fppg
    else:
        # Estimate based on salary (rough approximation)
        base = salary * 0.8  # 80% of salary as base projection
    
    # Adjust by position (QBs and RBs typically score higher)
    position_multipliers = {
        "QB": 1.2,
        "RB": 1.1,
        "WR": 1.0,
        "TE": 0.9,
        "K": 0.7,
        "DEF": 0.8,
    }
    
    multiplier = position_multipliers.get(position.upper(), 1.0)
    return base * multiplier


if __name__ == "__main__":
    asyncio.run(main()) 