#!/usr/bin/env python3
"""
Yahoo DFS Lineup Optimizer using pydfs-lineup-optimizer library.

This script demonstrates how to:
1. Load player projections from CSV
2. Get contest constraints from Yahoo DFS
3. Generate optimal lineups using the pydfs-lineup-optimizer library
"""

import asyncio
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_collection import YahooDFSCollector, SportType


def load_projections_from_csv(csv_file: str) -> List[Dict[str, Any]]:
    """Load player projections from CSV file."""
    projections = []
    
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            projections.append(row)
    
    return projections


def create_yahoo_players_csv(projections: List[Dict[str, Any]], output_file: str, use_consensus: bool = False) -> None:
    """
    Create Yahoo-compatible CSV format for the optimizer.
    
    The pydfs-lineup-optimizer expects specific column names:
    - First Name, Last Name, Position, Team, Salary, FPPG
    
    Args:
        projections: List of player projections
        output_file: Output CSV file path
        use_consensus: If True, use consensus projections for FPPG instead of actual FPPG
    """
    # Group projections by player to get consensus
    player_data = {}
    
    for proj in projections:
        player_name = proj["player_name"]
        source = proj["source"]
        projection = float(proj["projection"])
        
        if player_name not in player_data:
            player_data[player_name] = {
                "projections": [],
                "position": proj["position"],
                "team": proj["team"],
                "salary": int(proj["salary"]),
                "fppg": float(proj["fppg"]) if proj["fppg"] else 0.0,
                "opponent": proj["opponent"],
                "game_time": proj["game_time"]
            }
        
        player_data[player_name]["projections"].append(projection)
    
    # Calculate consensus projection (simple average for now)
    for player_name, data in player_data.items():
        if data["projections"]:
            data["consensus_projection"] = sum(data["projections"]) / len(data["projections"])
        else:
            data["consensus_projection"] = 0.0
    
    # Write Yahoo-compatible CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        fieldnames = [
            "ID", "First Name", "Last Name", "Position", "Team", "Game", 
            "Salary", "FPPG", "Injury Status", "Consensus Projection"
        ]
        
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        
        for player_name, data in player_data.items():
            # Split player name into first and last
            name_parts = player_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            else:
                first_name = player_name
                last_name = ""
            
            # Create game info (Team@Opponent format)
            game = f"{data['team']}@{data['opponent']}" if data['team'] and data['opponent'] else ""
            
            # Generate a simple ID (hash of name)
            import hashlib
            player_id = hashlib.md5(player_name.encode()).hexdigest()[:8]
            
            # Use consensus projections for FPPG if requested
            fppg_value = data["consensus_projection"] if use_consensus else data["fppg"]
            
            writer.writerow({
                "ID": player_id,
                "First Name": first_name,
                "Last Name": last_name,
                "Position": data["position"],
                "Team": data["team"],
                "Game": game,
                "Salary": data["salary"],
                "FPPG": round(fppg_value, 1),
                "Injury Status": "",  # No injury data in our dummy projections
                "Consensus Projection": round(data["consensus_projection"], 1),
            })
    
    projection_type = "consensus" if use_consensus else "FPPG"
    print(f"✅ Created Yahoo-compatible CSV: {output_file}")
    print(f"📊 Total players: {len(player_data)}")
    print(f"🎯 Using {projection_type} projections for optimization")


async def get_contest_info() -> Dict[str, Any]:
    """Get contest information including salary cap from Yahoo DFS."""
    yahoo_collector = YahooDFSCollector()
    
    # Get NFL contests
    contests = await yahoo_collector.collect_contests(SportType.NFL, multi_entry_only=True)
    
    if not contests:
        raise ValueError("No contests found")
    
    # Use first contest for demo
    contest = contests[0]
    
    # Get contest details
    contest_info = {
        "contest_id": contest.contest_id,
        "contest_name": contest.contest_name,
        "entry_fee": contest.entry_fee,
        "total_prize_pool": contest.total_prize_pool,
        "max_entries": contest.max_entries,
        "max_entries_per_user": contest.max_entries_per_user,
        "contest_type": contest.contest_type,
        "guaranteed": contest.guaranteed,
    }
    
    print(f"📊 Contest: {contest.contest_name}")
    print(f"💰 Entry Fee: ${contest.entry_fee}")
    print(f"🏆 Prize Pool: ${contest.total_prize_pool:,}")
    print(f"👥 Max Entries: {contest.max_entries}")
    print(f"🎯 Max Per User: {contest.max_entries_per_user}")
    
    return contest_info


def optimize_lineups(csv_file: str, num_lineups: int = 5) -> None:
    """
    Optimize lineups using pydfs-lineup-optimizer library.
    
    Args:
        csv_file: Path to Yahoo-compatible CSV
        num_lineups: Number of optimal lineups to generate
    """
    try:
        from pydfs_lineup_optimizer import Site, Sport, get_optimizer
        
        print(f"\n🚀 Optimizing {num_lineups} lineups using pydfs-lineup-optimizer...")
        
        # Create optimizer for Yahoo NFL
        optimizer = get_optimizer(Site.YAHOO, Sport.FOOTBALL)
        
        # Load players from CSV
        optimizer.load_players_from_csv(csv_file)
        
        # Get available positions (Yahoo NFL uses standard positions)
        yahoo_nfl_positions = ["QB", "RB", "WR", "TE", "K", "DEF"]
        print(f"📋 Yahoo NFL positions: {yahoo_nfl_positions}")
        
        # Generate optimal lineups
        lineups = list(optimizer.optimize(num_lineups))
        
        print(f"\n🏆 Generated {len(lineups)} optimal lineups:")
        
        for i, lineup in enumerate(lineups, 1):
            print(f"\n📊 Lineup {i}:")
            print(f"   Total Salary: ${lineup.salary_costs:,}")
            
            # Try different possible attribute names for fantasy points
            fantasy_points = getattr(lineup, 'fantasy_points', None)
            if fantasy_points is None:
                fantasy_points = getattr(lineup, 'points', None)
            if fantasy_points is None:
                fantasy_points = getattr(lineup, 'projected_points', None)
            if fantasy_points is None:
                fantasy_points = 0.0  # Default if no points attribute found
            
            print(f"   Projected Points: {fantasy_points:.1f}")
            print(f"   Players:")
            
            for player in lineup.lineup:
                # Try different possible attribute names for player fantasy points
                player_points = getattr(player, 'fantasy_points', None)
                if player_points is None:
                    player_points = getattr(player, 'points', None)
                if player_points is None:
                    player_points = getattr(player, 'projected_points', None)
                if player_points is None:
                    player_points = 0.0  # Default if no points attribute found
                
                # Get position (it's 'positions' not 'position')
                positions = getattr(player, 'positions', [])
                position_str = '/'.join(positions) if positions else 'Unknown'
                
                print(f"     {position_str}: {player.first_name} {player.last_name} "
                      f"({player.team}) - ${player.salary:,} - {player_points:.1f} pts")
        
        # Show lineup statistics
        if lineups:
            total_salaries = [lineup.salary_costs for lineup in lineups]
            
            # Get fantasy points for each lineup
            total_points = []
            for lineup in lineups:
                fantasy_points = getattr(lineup, 'fantasy_points', None)
                if fantasy_points is None:
                    fantasy_points = getattr(lineup, 'points', None)
                if fantasy_points is None:
                    fantasy_points = getattr(lineup, 'projected_points', None)
                if fantasy_points is None:
                    fantasy_points = 0.0
                total_points.append(fantasy_points)
            
            print(f"\n📈 Lineup Statistics:")
            print(f"   Average Salary: ${sum(total_salaries) / len(total_salaries):,.0f}")
            if any(total_points):
                print(f"   Average Points: {sum(total_points) / len(total_points):.1f}")
                print(f"   Best Lineup: {total_points.index(max(total_points)) + 1} "
                      f"({max(total_points):.1f} pts)")
            print(f"   Salary Range: ${min(total_salaries):,} - ${max(total_salaries):,}")
        
        # Note about FPPG usage
        print(f"\n💡 Note: The optimizer uses the 'FPPG' column for projections.")
        print(f"   Our consensus projections are in the 'Consensus Projection' column.")
        print(f"   To use consensus projections, you can modify the CSV to copy")
        print(f"   consensus values to the FPPG column before optimization.")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure pydfs-lineup-optimizer is installed:")
        print("   uv add pydfs-lineup-optimizer")
    except Exception as e:
        print(f"❌ Optimization failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function to run the lineup optimizer."""
    
    # File paths
    dummy_csv = Path(__file__).parent / "dummy_projections.csv"
    yahoo_csv = Path(__file__).parent / "yahoo_players.csv"
    
    print("🎯 Yahoo DFS Lineup Optimizer")
    print("=" * 40)
    
    # Check if dummy projections exist
    if not dummy_csv.exists():
        print("❌ Dummy projections CSV not found!")
        print("💡 Run: make create-dummy-projections")
        return
    
    # Load projections
    print("📊 Loading player projections...")
    projections = load_projections_from_csv(str(dummy_csv))
    print(f"✅ Loaded {len(projections)} projections")
    
    # Create Yahoo-compatible CSV
    print("\n🔄 Converting to Yahoo format...")
    create_yahoo_players_csv(projections, str(yahoo_csv), use_consensus=True)
    
    # Get contest info
    print("\n🏈 Getting contest information...")
    try:
        contest_info = await get_contest_info()
    except Exception as e:
        print(f"⚠️  Could not get contest info: {e}")
        print("   Using default settings...")
        contest_info = {}
    
    # Optimize lineups
    print("\n🎯 Starting lineup optimization...")
    optimize_lineups(str(yahoo_csv), num_lineups=5)
    
    print(f"\n✨ Lineup optimization complete!")
    print(f"📁 Files created:")
    print(f"   - {dummy_csv.name} (original projections)")
    print(f"   - {yahoo_csv.name} (Yahoo format)")
    
    # Cleanup
    if yahoo_csv.exists():
        yahoo_csv.unlink()
        print(f"🧹 Cleaned up temporary file: {yahoo_csv.name}")


if __name__ == "__main__":
    asyncio.run(main()) 