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

from . import YahooDFSCollector, SportType


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


def optimize_lineups(projections_file: str, contest_info: Dict[str, Any], num_lineups: int = 1) -> List[Dict[str, Any]]:
    """
    Optimize lineups using pydfs-lineup-optimizer.
    
    Args:
        projections_file: Path to CSV file with player projections
        contest_info: Contest information including slate_type and salary_cap
        num_lineups: Number of lineups to generate
        
    Returns:
        List of optimized lineups
    """
    try:
        from pydfs_lineup_optimizer import get_optimizer, Site, Sport
        from pydfs_lineup_optimizer.sites.yahoo.settings import YahooFootballSettings
        
        # Determine if this is a single game contest
        is_single_game = contest_info.get('slate_type') == 'SINGLE_GAME'
        salary_cap = contest_info.get('salary_cap', 200)
        
        print(f"🎯 Contest Type: {'Single Game' if is_single_game else 'Multi Game'}")
        print(f"💰 Salary Cap: ${salary_cap:,}")
        
        # Create the appropriate optimizer based on contest type
        if is_single_game:
            print(f"🏈 Single Game Contest - Using 5-player structure (1 MVP + 4 UTIL)")
            # Convert Yahoo CSV to FanDuel single game format
            import tempfile
            import os
            
            # Create temporary FanDuel CSV
            temp_dir = tempfile.gettempdir()
            fanduel_csv = os.path.join(temp_dir, f"fanduel_single_game_{os.getpid()}.csv")
            
            try:
                convert_yahoo_to_fanduel_single_game_csv(projections_file, fanduel_csv)
                optimizer = create_yahoo_single_game_optimizer(salary_cap)
                optimizer.load_players_from_csv(fanduel_csv)
            finally:
                # Clean up temporary file
                if os.path.exists(fanduel_csv):
                    os.unlink(fanduel_csv)
        else:
            print(f"🏈 Multi Game Contest - Using standard 9-player structure")
            optimizer = get_optimizer(Site.YAHOO, Sport.FOOTBALL)
            optimizer.settings.budget = salary_cap
            optimizer.load_players_from_csv(projections_file)
        
        print(f"📊 Loaded {len(optimizer.players)} players")
        print(f"🎯 Available positions: {', '.join(sorted(optimizer.available_positions))}")
        print(f"💰 Budget: ${optimizer.budget:,}")
        
        # Generate lineups
        print(f"🚀 Generating {num_lineups} lineup(s)...")
        lineups = list(optimizer.optimize(num_lineups))
        
        if not lineups:
            print("❌ No valid lineups found!")
            return []
        
        print(f"✅ Successfully generated {len(lineups)} lineup(s)")
        
        # Convert lineups to our format
        formatted_lineups = []
        for i, lineup in enumerate(lineups):
            try:
                # Get total fantasy points
                fantasy_points = getattr(lineup, 'fantasy_points', 
                                      getattr(lineup, 'points', 
                                             getattr(lineup, 'projected_points', 0.0)))
                
                # Get total salary
                total_salary = sum(player.salary for player in lineup.lineup)
                
                # Format players
                players = []
                for player in lineup.lineup:
                    # Get player fantasy points
                    player_points = getattr(player, 'fantasy_points', 
                                          getattr(player, 'points', 
                                                 getattr(player, 'projected_points', 0.0)))
                    
                    players.append({
                        "player_name": player.first_name + " " + player.last_name,
                        "position": '/'.join(player.positions),
                        "team": player.team,
                        "salary": player.salary,
                        "projection": player_points,
                        "fppg": player.fppg
                    })
                
                formatted_lineup = {
                    "lineup_id": f"{contest_info.get('contest_id', 'unknown')}_{i+1}",
                    "contest_id": contest_info.get('contest_id', 'unknown'),
                    "contest_name": contest_info.get('contest_name', 'Unknown Contest'),
                    "entry_fee": contest_info.get('entry_fee', 0),
                    "total_salary": total_salary,
                    "projected_points": fantasy_points,
                    "players": players
                }
                
                formatted_lineups.append(formatted_lineup)
                
            except Exception as e:
                print(f"⚠️ Error formatting lineup {i+1}: {e}")
                continue
        
        return formatted_lineups
        
    except ImportError:
        print("❌ pydfs-lineup-optimizer not installed!")
        print("Install with: uv add pydfs-lineup-optimizer")
        return []
    except Exception as e:
        print(f"❌ Error optimizing lineups: {e}")
        return []


def convert_yahoo_to_fanduel_single_game_csv(yahoo_csv_path: str, fanduel_csv_path: str):
    """
    Convert Yahoo CSV format to FanDuel single game CSV format.
    
    Args:
        yahoo_csv_path: Path to Yahoo format CSV
        fanduel_csv_path: Path to save FanDuel format CSV
    """
    import pandas as pd
    import csv
    
    # Read Yahoo CSV
    df = pd.read_csv(yahoo_csv_path)
    
    # Create FanDuel single game CSV
    with open(fanduel_csv_path, 'w', newline='', encoding='utf-8') as file:
        fieldnames = ['Id', 'First Name', 'Last Name', 'Position', 'Team', 'Salary', 'FPPG', 'Game', 'Injury Indicator']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        
        for _, row in df.iterrows():
            # Split name into first and last
            full_name = row['First Name']
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
            else:
                first_name = full_name
                last_name = ''
            
            # Create game info (Team@Opponent format)
            game = row['Game'] if pd.notna(row['Game']) else f"{row['Team']}@OPP"
            
            # Handle injury indicator
            injury_indicator = row.get('Injury Status', '')
            if pd.isna(injury_indicator):
                injury_indicator = ''
            
            # Write row in FanDuel format
            writer.writerow({
                'Id': row['ID'],
                'First Name': first_name,
                'Last Name': last_name,
                'Position': row['Position'],
                'Team': row['Team'],
                'Salary': row['Salary'],
                'FPPG': row['FPPG'],
                'Game': game,
                'Injury Indicator': injury_indicator
            })
    
    print(f"✅ Converted Yahoo CSV to FanDuel single game format: {fanduel_csv_path}")


def create_yahoo_single_game_optimizer(salary_cap: int = 135):
    """
    Create a Yahoo single game optimizer using FanDuel single game structure.
    
    Args:
        salary_cap: Salary cap for single game contests (default 135)
        
    Returns:
        Single game optimizer with Yahoo budget
    """
    from pydfs_lineup_optimizer import get_optimizer, Site, Sport
    
    # Use FanDuel single game optimizer but with custom budget
    optimizer = get_optimizer(Site.FANDUEL_SINGLE_GAME, Sport.FOOTBALL)
    
    # Override the budget to match Yahoo's single game budget
    optimizer.settings.budget = salary_cap
    
    return optimizer


def main():
    """Main function to run lineup optimization."""
    
    # File paths
    projections_file = Path("examples/dummy_projections.csv")
    yahoo_csv = Path("examples/yahoo_players.csv")
    
    if not projections_file.exists():
        print(f"❌ Projections file not found: {projections_file}")
        return
    
    print("🚀 Starting DFS Lineup Optimization")
    print("=" * 50)
    
    # Load projections from CSV
    print("📊 Loading projections from CSV...")
    projections = load_projections_from_csv(str(projections_file))
    print(f"✅ Loaded {len(projections)} projections")
    
    # Create contest info (this would normally come from actual contest data)
    contest_info = {
        "contest_id": "test_contest_123",
        "contest_name": "Test NFL Contest",
        "entry_fee": 1.0,
        "slate_type": "MULTI_GAME",  # Can be "SINGLE_GAME" or "MULTI_GAME"
        "salary_cap": 200  # Will be 135 for single game, 200 for multi game
    }
    
    print(f"🏈 Contest: {contest_info['contest_name']}")
    print(f"💰 Entry Fee: ${contest_info['entry_fee']}")
    print(f"🎯 Slate Type: {contest_info['slate_type']}")
    print(f"💰 Salary Cap: ${contest_info['salary_cap']:,}")
    
    # Create Yahoo-compatible CSV
    print("\n📊 Creating Yahoo-compatible CSV...")
    create_yahoo_players_csv(projections, yahoo_csv, use_consensus=True)
    
    # Optimize lineups
    print("\n🎯 Starting lineup optimization...")
    lineups = optimize_lineups(str(yahoo_csv), contest_info, num_lineups=5)
    
    if lineups:
        print(f"\n🏆 Generated {len(lineups)} lineups:")
        for i, lineup in enumerate(lineups, 1):
            print(f"\n📊 Lineup {i}:")
            print(f"   Contest: {lineup['contest_name']}")
            print(f"   Total Salary: ${lineup['total_salary']:,}")
            print(f"   Projected Points: {lineup['projected_points']:.1f}")
            print(f"   Players:")
            for player in lineup['players']:
                print(f"     {player['position']}: {player['player_name']} "
                      f"({player['team']}) - ${player['salary']:,} - {player['projection']:.1f} pts")
    
    print(f"\n✨ Lineup optimization complete!")


if __name__ == "__main__":
    main() 