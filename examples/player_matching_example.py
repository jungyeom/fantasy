#!/usr/bin/env python3
"""
Example demonstrating player name matching and projection consensus.

This script shows how to:
1. Get Yahoo DFS players for a contest
2. Match player names across different projection sources
3. Determine consensus projections
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_collection import (
    YahooDFSCollector,
    PlayerNameMatcher,
    ProjectionConsensus,
    ProjectionAggregator,
    SportType,
)


async def main():
    """Demonstrate player matching and projection consensus."""
    
    # Initialize components
    yahoo_collector = YahooDFSCollector()
    name_matcher = PlayerNameMatcher()
    consensus = ProjectionConsensus()
    aggregator = ProjectionAggregator(consensus)
    
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
    
    # Cache Yahoo players for matching
    name_matcher.cache_yahoo_players(contest.contest_id, list(yahoo_players.values()))
    
    # Debug: Show some actual player names
    print(f"\n🔍 Sample Yahoo player names:")
    for i, yahoo_name in enumerate(list(yahoo_players.keys())[:5]):
        print(f"  {i+1}. '{yahoo_name}'")
    
    # Simulate projections from different sources
    print("\n📈 Simulating projections from different sources...")
    
    # Example: Simulate Daily Fantasy Fuel projections (using actual Yahoo names)
    sample_yahoo_names = list(yahoo_players.keys())[:10]
    dff_projections = {
        sample_yahoo_names[0] if len(sample_yahoo_names) > 0 else "dak prescott": 25.5,
        sample_yahoo_names[1] if len(sample_yahoo_names) > 1 else "miles sanders": 28.2,
        sample_yahoo_names[2] if len(sample_yahoo_names) > 2 else "ceeedee lamb": 22.8,
        sample_yahoo_names[3] if len(sample_yahoo_names) > 3 else "justin jefferson": 24.1,
    }
    
    # Example: Simulate Rotowire projections (using actual Yahoo names)
    rotowire_projections = {
        sample_yahoo_names[0] if len(sample_yahoo_names) > 0 else "dak prescott": 26.1,
        sample_yahoo_names[1] if len(sample_yahoo_names) > 1 else "miles sanders": 27.9,
        sample_yahoo_names[2] if len(sample_yahoo_names) > 2 else "ceeedee lamb": 23.2,
        sample_yahoo_names[3] if len(sample_yahoo_names) > 3 else "justin jefferson": 23.8,
    }
    
    # Match players and create projection data
    all_player_projections = {}
    
    for yahoo_name in list(yahoo_players.keys())[:10]:  # Test with first 10 players
        player_projections = {}
        
        # Try to match with DFF projections
        dff_match = name_matcher.find_best_match(yahoo_name, list(dff_projections.keys()))
        if dff_match:
            player_projections["dailyfantasyfuel"] = dff_projections[dff_match]
        
        # Try to match with Rotowire projections
        rotowire_match = name_matcher.find_best_match(yahoo_name, list(rotowire_projections.keys()))
        if rotowire_match:
            player_projections["rotowire"] = rotowire_projections[rotowire_match]
        
        if player_projections:
            all_player_projections[yahoo_name] = player_projections
    
    print(f"🎯 Successfully matched {len(all_player_projections)} players with projections")
    
    # Get consensus projections
    print("\n🏆 Consensus Projections:")
    aggregated = aggregator.aggregate_player_projections(all_player_projections)
    
    for player_name, data in aggregated.items():
        print(f"\n{player_name.title()}:")
        print(f"  Consensus: {data['consensus_projection']:.1f}")
        print(f"  Best Source: {data['best_source']}")
        print(f"  Sources: {data['projection_count']}")
        
        # Show individual projections
        for source, value in data['all_projections'].items():
            print(f"    {source}: {value:.1f}")
    
    # Show source rankings
    print(f"\n📊 Source Rankings (by weight):")
    for source, weight in consensus.get_source_weights().items():
        print(f"  {source}: {weight:.1%}")


if __name__ == "__main__":
    asyncio.run(main()) 