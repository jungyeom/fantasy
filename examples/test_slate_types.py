#!/usr/bin/env python3
"""
Test script to verify slate types and budget handling for single vs multi game contests.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_collection import YahooDFSCollector, SportType

async def main():
    """Test slate types and budget handling."""
    
    yahoo_collector = YahooDFSCollector()
    
    print("🔍 Testing slate types and budget handling...")
    
    # Get all contests (both single and multi game)
    print("\n📊 Fetching all contests with slate types...")
    all_contests = await yahoo_collector.collect_contests(SportType.NFL, multi_entry_only=False)
    print(f"✅ Found {len(all_contests)} total contests")
    
    # Categorize contests by type
    single_game_contests = []
    multi_game_contests = []
    unknown_type_contests = []
    
    for contest in all_contests:
        # Try to determine contest type from name or other attributes
        contest_name = contest.contest_name.lower()
        
        if any(keyword in contest_name for keyword in ['single', 'one game', '1 game', 'primetime']):
            single_game_contests.append(contest)
        elif any(keyword in contest_name for keyword in ['multi', 'full slate', 'main slate', 'all games']):
            multi_game_contests.append(contest)
        else:
            unknown_type_contests.append(contest)
    
    print(f"\n🎯 Contest Type Breakdown:")
    print(f"  Single Game: {len(single_game_contests)}")
    print(f"  Multi Game: {len(multi_game_contests)}")
    print(f"  Unknown: {len(unknown_type_contests)}")
    
    # Show sample single game contests
    if single_game_contests:
        print(f"\n🏈 Sample Single Game Contests:")
        for i, contest in enumerate(single_game_contests[:5]):
            print(f"  {i+1}. {contest.contest_name}")
            print(f"     Entry Fee: ${contest.entry_fee}")
            print(f"     Prize Pool: ${contest.total_prize_pool:,}")
            print(f"     Max Entries: {contest.max_entries}")
            print(f"     Max Per User: {contest.max_entries_per_user}")
            print(f"     Contest ID: {contest.contest_id}")
    
    # Show sample multi game contests
    if multi_game_contests:
        print(f"\n🏈 Sample Multi Game Contests:")
        for i, contest in enumerate(multi_game_contests[:5]):
            print(f"  {i+1}. {contest.contest_name}")
            print(f"     Entry Fee: ${contest.entry_fee}")
            print(f"     Prize Pool: ${contest.total_prize_pool:,}")
            print(f"     Max Entries: {contest.max_entries}")
            print(f"     Max Per User: {contest.max_entries_per_user}")
            print(f"     Contest ID: {contest.contest_id}")
    
    # Analyze budget patterns
    print(f"\n💰 Budget Analysis:")
    
    # Single game budgets
    if single_game_contests:
        single_budgets = [contest.max_entries for contest in single_game_contests if contest.max_entries > 0]
        if single_budgets:
            avg_single_budget = sum(single_budgets) / len(single_budgets)
            print(f"  Single Game - Avg Budget: {avg_single_budget:.0f}")
            print(f"  Single Game - Min Budget: {min(single_budgets)}")
            print(f"  Single Game - Max Budget: {max(single_budgets)}")
    
    # Multi game budgets
    if multi_game_contests:
        multi_budgets = [contest.max_entries for contest in multi_game_contests if contest.max_entries > 0]
        if multi_budgets:
            avg_multi_budget = sum(multi_budgets) / len(multi_budgets)
            print(f"  Multi Game - Avg Budget: {avg_multi_budget:.0f}")
            print(f"  Multi Game - Min Budget: {min(multi_budgets)}")
            print(f"  Multi Game - Max Budget: {max(multi_budgets)}")
    
    # Test with a single game contest if available
    if single_game_contests:
        test_contest = single_game_contests[0]
        print(f"\n🧪 Testing Single Game Contest:")
        print(f"  Contest: {test_contest.contest_name}")
        print(f"  Contest ID: {test_contest.contest_id}")
        
        # Try to get players for this contest
        print(f"  Fetching players...")
        try:
            players = await yahoo_collector.get_players_with_ids(test_contest.contest_id)
            print(f"  ✅ Found {len(players)} players")
            
            if players:
                # Show sample player with budget info
                sample_player = players[0]
                print(f"  Sample Player: {sample_player.get('name', 'Unknown')}")
                print(f"    Position: {sample_player.get('Position', 'Unknown')}")
                print(f"    Salary: {sample_player.get('Salary', 'Unknown')}")
                print(f"    Team: {sample_player.get('Team', 'Unknown')}")
                
        except Exception as e:
            print(f"  ❌ Error fetching players: {e}")
    
    print(f"\n✨ Slate types test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 