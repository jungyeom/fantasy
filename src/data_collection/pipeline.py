#!/usr/bin/env python3
"""
DFS Pipeline: Complete data collection and lineup optimization pipeline.

This script orchestrates the entire process:
1. Collect contest information from Yahoo DFS
2. Collect projections from multiple sources (placeholder collectors)
3. Standardize player names and projections
4. Generate optimal lineups for qualifying contests
5. Save lineups to CSV files
"""

import asyncio
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from . import (
    YahooDFSCollector,
    DailyFantasyFuelCollector,
    BasketballReferenceCollector,
    PlayerNameMatcher,
    ProjectionConsensus,
    SportType,
)
from .lineup_optimizer import create_yahoo_players_csv


class DFSPipeline:
    """Main pipeline for DFS data collection and lineup optimization."""
    
    def __init__(self, output_dir: str = "lineups"):
        """
        Initialize the DFS pipeline.
        
        Args:
            output_dir: Directory to save generated lineups
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.yahoo_collector = YahooDFSCollector()
        self.name_matcher = PlayerNameMatcher()
        self.consensus = ProjectionConsensus()
        
        # Placeholder collectors (will be implemented later)
        self.collectors = {
            "dailyfantasyfuel": DailyFantasyFuelCollector(),
            "basketballreference": BasketballReferenceCollector(),
            # Add more collectors as they become available
        }
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / "pipeline.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def collect_contests(self, sport: SportType, max_entry_fee: float = 1.0) -> List[Dict[str, Any]]:
        """
        Collect qualifying contests from Yahoo DFS.
        
        Args:
            sport: Sport type to collect contests for
            max_entry_fee: Maximum entry fee to consider (default: $1)
            
        Returns:
            List of qualifying contests
        """
        self.logger.info(f"Collecting {sport.value} contests with max entry fee ${max_entry_fee}")
        
        try:
            # Get all multi-entry contests
            contests = await self.yahoo_collector.collect_contests(sport, multi_entry_only=True)
            
            if not contests:
                self.logger.warning(f"No {sport.value} contests found")
                return []
            
            # Filter by entry fee
            qualifying_contests = [
                contest for contest in contests 
                if contest.entry_fee <= max_entry_fee
            ]
            
            self.logger.info(f"Found {len(contests)} total contests, {len(qualifying_contests)} qualify (≤${max_entry_fee})")
            
            # Calculate total lineups needed
            total_lineups = sum(contest.max_entries_per_user for contest in qualifying_contests)
            self.logger.info(f"Total lineups to generate: {total_lineups}")
            
            return qualifying_contests
            
        except Exception as e:
            self.logger.error(f"Failed to collect contests: {e}")
            return []
    
    async def collect_projections(self, sport: SportType) -> Dict[str, List[Dict[str, Any]]]:
        """
        Collect projections from all available sources.
        
        Args:
            sport: Sport type to collect projections for
            
        Returns:
            Dictionary mapping source names to player projections
        """
        self.logger.info(f"Collecting projections for {sport.value}")
        
        all_projections = {}
        
        for source_name, collector in self.collectors.items():
            try:
                self.logger.info(f"Collecting from {source_name}...")
                
                # Placeholder: In off-season, return empty projections
                # TODO: Implement actual projection collection when collectors are ready
                if sport == SportType.NFL:
                    projections = self._get_placeholder_nfl_projections(source_name)
                elif sport == SportType.NBA:
                    projections = self._get_placeholder_nba_projections(source_name)
                else:
                    projections = []
                
                all_projections[source_name] = projections
                self.logger.info(f"Collected {len(projections)} projections from {source_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to collect from {source_name}: {e}")
                all_projections[source_name] = []
        
        return all_projections
    
    def _get_placeholder_nfl_projections(self, source: str) -> List[Dict[str, Any]]:
        """Generate placeholder NFL projections for testing."""
        # Expanded sample players for testing
        sample_players = [
            # QBs
            {"name": "Patrick Mahomes", "position": "QB", "team": "KC", "salary": 35, "projection": 25.5},
            {"name": "Josh Allen", "position": "QB", "team": "BUF", "salary": 34, "projection": 24.8},
            {"name": "Lamar Jackson", "position": "QB", "team": "BAL", "salary": 33, "projection": 23.9},
            {"name": "Jalen Hurts", "position": "QB", "team": "PHI", "salary": 32, "projection": 22.7},
            {"name": "Dak Prescott", "position": "QB", "team": "DAL", "salary": 31, "projection": 21.5},
            {"name": "Justin Herbert", "position": "QB", "team": "LAC", "salary": 30, "projection": 20.8},
            {"name": "Joe Burrow", "position": "QB", "team": "CIN", "salary": 29, "projection": 19.9},
            {"name": "Trevor Lawrence", "position": "QB", "team": "JAX", "salary": 28, "projection": 18.7},
            {"name": "Tua Tagovailoa", "position": "QB", "team": "MIA", "salary": 27, "projection": 17.8},
            {"name": "Kirk Cousins", "position": "QB", "team": "MIN", "salary": 26, "projection": 16.9},
            
            # RBs
            {"name": "Christian McCaffrey", "position": "RB", "team": "SF", "salary": 38, "projection": 28.2},
            {"name": "Saquon Barkley", "position": "RB", "team": "PHI", "salary": 37, "projection": 27.5},
            {"name": "Derrick Henry", "position": "RB", "team": "BAL", "salary": 36, "projection": 26.8},
            {"name": "Nick Chubb", "position": "RB", "team": "CLE", "salary": 35, "projection": 25.9},
            {"name": "Alvin Kamara", "position": "RB", "team": "NO", "salary": 34, "projection": 24.7},
            {"name": "Austin Ekeler", "position": "RB", "team": "LAC", "salary": 33, "projection": 23.8},
            {"name": "Joe Mixon", "position": "RB", "team": "CIN", "salary": 32, "projection": 22.9},
            {"name": "Miles Sanders", "position": "RB", "team": "CAR", "salary": 31, "projection": 21.7},
            {"name": "Jahmyr Gibbs", "position": "RB", "team": "DET", "salary": 30, "projection": 20.8},
            {"name": "Breece Hall", "position": "RB", "team": "NYJ", "salary": 29, "projection": 19.9},
            
            # WRs
            {"name": "Tyreek Hill", "position": "WR", "team": "MIA", "salary": 32, "projection": 24.8},
            {"name": "CeeDee Lamb", "position": "WR", "team": "DAL", "salary": 31, "projection": 23.9},
            {"name": "Justin Jefferson", "position": "WR", "team": "MIN", "salary": 30, "projection": 22.8},
            {"name": "Amon-Ra St. Brown", "position": "WR", "team": "DET", "salary": 29, "projection": 21.7},
            {"name": "Stefon Diggs", "position": "WR", "team": "HOU", "salary": 28, "projection": 20.8},
            {"name": "Davante Adams", "position": "WR", "team": "LV", "salary": 27, "projection": 19.9},
            {"name": "Cooper Kupp", "position": "WR", "team": "LAR", "salary": 26, "projection": 18.7},
            {"name": "Deebo Samuel", "position": "WR", "team": "SF", "salary": 25, "projection": 17.8},
            {"name": "Brandon Aiyuk", "position": "WR", "team": "SF", "salary": 24, "projection": 16.9},
            {"name": "Tee Higgins", "position": "WR", "team": "CIN", "salary": 23, "projection": 15.8},
            
            # TEs
            {"name": "Travis Kelce", "position": "TE", "team": "KC", "salary": 28, "projection": 22.1},
            {"name": "Mark Andrews", "position": "TE", "team": "BAL", "salary": 27, "projection": 21.2},
            {"name": "T.J. Hockenson", "position": "TE", "team": "MIN", "salary": 26, "projection": 20.3},
            {"name": "George Kittle", "position": "TE", "team": "SF", "salary": 25, "projection": 19.4},
            {"name": "Sam LaPorta", "position": "TE", "team": "DET", "salary": 24, "projection": 18.5},
            {"name": "Evan Engram", "position": "TE", "team": "JAX", "salary": 23, "projection": 17.6},
            {"name": "Jake Ferguson", "position": "TE", "team": "DAL", "salary": 22, "projection": 16.7},
            {"name": "Taysom Hill", "position": "TE", "team": "NO", "salary": 21, "projection": 15.8},
            {"name": "Cole Kmet", "position": "TE", "team": "CHI", "salary": 20, "projection": 14.9},
            {"name": "Pat Freiermuth", "position": "TE", "team": "PIT", "salary": 19, "projection": 13.8},
            
            # Ks
            {"name": "Justin Tucker", "position": "K", "team": "BAL", "salary": 15, "projection": 9.5},
            {"name": "Harrison Butker", "position": "K", "team": "KC", "salary": 14, "projection": 8.8},
            {"name": "Evan McPherson", "position": "K", "team": "CIN", "salary": 13, "projection": 8.1},
            {"name": "Younghoe Koo", "position": "K", "team": "ATL", "salary": 12, "projection": 7.4},
            {"name": "Daniel Carlson", "position": "K", "team": "LV", "salary": 11, "projection": 6.7},
            {"name": "Greg Zuerlein", "position": "K", "team": "NYJ", "salary": 10, "projection": 6.0},
            {"name": "Matt Gay", "position": "K", "team": "IND", "salary": 9, "projection": 5.3},
            {"name": "Brandon McManus", "position": "K", "team": "JAX", "salary": 8, "projection": 4.6},
            {"name": "Cameron Dicker", "position": "K", "team": "LAC", "salary": 7, "projection": 3.9},
            {"name": "Jake Elliott", "position": "K", "team": "PHI", "salary": 6, "projection": 3.2},
            
            # DEFs
            {"name": "San Francisco 49ers", "position": "DEF", "team": "SF", "salary": 18, "projection": 12.3},
            {"name": "Dallas Cowboys", "position": "DEF", "team": "DAL", "salary": 17, "projection": 11.6},
            {"name": "Buffalo Bills", "position": "DEF", "team": "BUF", "salary": 16, "projection": 10.9},
            {"name": "Baltimore Ravens", "position": "DEF", "team": "BAL", "salary": 15, "projection": 10.2},
            {"name": "New England Patriots", "position": "DEF", "team": "NE", "salary": 14, "projection": 9.5},
            {"name": "Philadelphia Eagles", "position": "DEF", "team": "PHI", "salary": 13, "projection": 8.8},
            {"name": "Miami Dolphins", "position": "DEF", "team": "MIA", "salary": 12, "projection": 8.1},
            {"name": "New York Jets", "position": "DEF", "team": "NYJ", "salary": 11, "projection": 7.4},
            {"name": "Cleveland Browns", "position": "DEF", "team": "CLE", "salary": 10, "projection": 6.7},
            {"name": "Denver Broncos", "position": "DEF", "team": "DEN", "salary": 9, "projection": 6.0},
        ]
        
        projections = []
        for player in sample_players:
            # Add some variation based on source
            import random
            variation = random.uniform(0.9, 1.1)
            adjusted_projection = player["projection"] * variation
            
            projections.append({
                "player_name": player["name"],
                "source": source,
                "projection": round(adjusted_projection, 1),
                "confidence": round(random.uniform(0.7, 0.95), 2),
                "position": player["position"],
                "salary": player["salary"],
                "fppg": player["projection"],
                "team": player["team"],
                "opponent": "TBD",
                "game_time": "TBD",
            })
        
        return projections
    
    def _get_placeholder_nba_projections(self, source: str) -> List[Dict[str, Any]]:
        """Generate placeholder NBA projections for testing."""
        # Sample NBA players for testing
        sample_players = [
            {"name": "Nikola Jokic", "position": "C", "team": "DEN", "salary": 42, "projection": 55.2},
            {"name": "Luka Doncic", "position": "PG", "team": "DAL", "salary": 40, "projection": 52.8},
            {"name": "Joel Embiid", "position": "C", "team": "PHI", "salary": 38, "projection": 48.5},
            {"name": "Giannis Antetokounmpo", "position": "PF", "team": "MIL", "salary": 39, "projection": 51.2},
            {"name": "Stephen Curry", "position": "PG", "team": "GSW", "salary": 36, "projection": 45.8},
        ]
        
        projections = []
        for player in sample_players:
            import random
            variation = random.uniform(0.9, 1.1)
            adjusted_projection = player["projection"] * variation
            
            projections.append({
                "player_name": player["name"],  # This should match what the pipeline expects
                "source": source,
                "projection": round(adjusted_projection, 1),
                "confidence": round(random.uniform(0.7, 0.95), 2),
                "position": player["position"],
                "salary": player["salary"],
                "fppg": player["projection"],
                "team": player["team"],
                "opponent": "TBD",
                "game_time": "TBD",
            })
        
        return projections
    
    async def standardize_projections(self, all_projections: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Standardize projections across different sources.
        
        Args:
            all_projections: Dictionary mapping source names to player projections
            
        Returns:
            List of standardized projections in dummy_projections.csv format
        """
        self.logger.info("Standardizing projections across sources...")
        
        # Flatten all projections into a single list
        all_flat_projections = []
        for source, projections in all_projections.items():
            for projection in projections:
                all_flat_projections.append(projection)
        
        self.logger.info(f"Total projections to standardize: {len(all_flat_projections)}")
        
        # For now, return as-is since we're using placeholder data
        # TODO: Implement actual name standardization when real collectors are available
        return all_flat_projections
    
    async def generate_lineups_for_contest(self, contest: Any, projections: List[Dict[str, Any]], 
                                         num_lineups: int) -> List[Dict[str, Any]]:
        """
        Generate optimal lineups for a specific contest.
        
        Args:
            contest: Contest information (YahooContest object)
            projections: Player projections
            num_lineups: Number of lineups to generate
            
        Returns:
            List of generated lineups
        """
        self.logger.info(f"Generating {num_lineups} lineups for contest: {getattr(contest, 'contest_name', 'Unknown')}")
        
        try:
            # Create temporary CSV for the optimizer
            temp_csv = self.output_dir / f"temp_contest_{getattr(contest, 'contest_id', 'unknown')}.csv"
            
            # Create Yahoo-compatible CSV
            create_yahoo_players_csv(projections, str(temp_csv), use_consensus=True)
            
            # TODO: Integrate with actual lineup optimizer
            # For now, return placeholder lineups
            lineups = self._generate_placeholder_lineups(contest, projections, num_lineups)
            
            # Clean up temp file
            if temp_csv.exists():
                temp_csv.unlink()
            
            return lineups
            
        except Exception as e:
            self.logger.error(f"Failed to generate lineups for contest: {e}")
            return []
    
    def _generate_placeholder_lineups(self, contest: Any, projections: List[Dict[str, Any]], 
                                    num_lineups: int) -> List[Dict[str, Any]]:
        """Generate placeholder lineups for testing."""
        lineups = []
        
        # Group projections by player
        player_projections = {}
        for proj in projections:
            player_name = proj["player_name"]
            if player_name not in player_projections:
                player_projections[player_name] = []
            player_projections[player_name].append(proj)
        
        # Generate lineups
        for i in range(num_lineups):
            lineup = {
                "lineup_id": f"{getattr(contest, 'contest_id', 'unknown')}_{i+1}",
                "contest_id": getattr(contest, "contest_id", "unknown"),
                "contest_name": getattr(contest, "contest_name", "Unknown"),
                "entry_fee": getattr(contest, "entry_fee", 0),
                "total_salary": 0,
                "projected_points": 0,
                "players": []
            }
            
            # Simple lineup construction (QB, RB, WR, TE, K, DEF for NFL)
            positions_needed = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "K", "DEF"]
            used_players = set()
            
            for pos in positions_needed:
                # Find available players for this position
                available = [
                    p for p in projections 
                    if p["position"] == pos and p["player_name"] not in used_players
                ]
                
                if available:
                    # Pick first available player
                    player = available[0]
                    lineup["players"].append({
                        "position": pos,
                        "player_name": player["player_name"],  # Changed from "name" to "player_name"
                        "team": player["team"],
                        "salary": player["salary"],
                        "projection": player["projection"]
                    })
                    lineup["total_salary"] += player["salary"]
                    lineup["projected_points"] += player["projection"]
                    used_players.add(player["player_name"])
            
            lineups.append(lineup)
        
        return lineups
    
    def save_lineups_to_csv(self, lineups: List[Dict[str, Any]], contest: Dict[str, Any]) -> str:
        """
        Save lineups to CSV file.
        
        Args:
            lineups: List of lineups to save
            contest: Contest information
            
        Returns:
            Path to saved CSV file
        """
        if not lineups:
            self.logger.warning("No lineups to save")
            return ""
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        contest_name = getattr(contest, "contest_name", "unknown").replace(" ", "_").replace("$", "").replace(",", "")
        filename = f"lineups_{contest_name}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Write lineups to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                "lineup_id", "contest_id", "contest_name", "entry_fee", 
                "total_salary", "projected_points", "position", "player_name", 
                "team", "salary", "projection"
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for lineup in lineups:
                for player in lineup["players"]:
                    writer.writerow({
                        "lineup_id": lineup["lineup_id"],
                        "contest_id": lineup["contest_id"],
                        "contest_name": lineup["contest_name"],
                        "entry_fee": lineup["entry_fee"],
                        "total_salary": lineup["total_salary"],
                        "projected_points": lineup["projected_points"],
                        "position": player["position"],
                        "player_name": player["player_name"],
                        "team": player["team"],
                        "salary": player["salary"],
                        "projection": player["projection"]
                    })
        
        self.logger.info(f"Saved {len(lineups)} lineups to {filepath}")
        return str(filepath)
    
    async def run_pipeline(self, sport: SportType, max_entry_fee: float = 1.0) -> Dict[str, Any]:
        """
        Run the complete DFS pipeline.
        
        Args:
            sport: Sport type to process
            max_entry_fee: Maximum entry fee to consider
            
        Returns:
            Pipeline results summary
        """
        self.logger.info(f"Starting DFS pipeline for {sport.value}")
        
        results = {
            "sport": sport.value,
            "contests_processed": 0,
            "total_lineups_generated": 0,
            "files_created": [],
            "errors": []
        }
        
        try:
            # Step 1: Collect qualifying contests
            contests = await self.collect_contests(sport, max_entry_fee)
            if not contests:
                self.logger.warning("No qualifying contests found")
                return results
            
            # Step 2: Collect projections from all sources
            all_projections = await self.collect_projections(sport)
            
            # Step 3: Standardize projections
            standardized_projections = await self.standardize_projections(all_projections)
            
            # Step 4: Generate lineups for each contest
            for contest in contests:
                try:
                    num_lineups = contest.max_entries_per_user
                    lineups = await self.generate_lineups_for_contest(
                        contest, standardized_projections, num_lineups
                    )
                    
                    if lineups:
                        # Save lineups to CSV
                        csv_file = self.save_lineups_to_csv(lineups, contest)
                        if csv_file:
                            results["files_created"].append(csv_file)
                            results["total_lineups_generated"] += len(lineups)
                    
                    results["contests_processed"] += 1
                    
                except Exception as e:
                    error_msg = f"Failed to process contest {getattr(contest, 'contest_id', 'unknown')}: {e}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            self.logger.info(f"Pipeline completed successfully!")
            self.logger.info(f"Processed {results['contests_processed']} contests")
            self.logger.info(f"Generated {results['total_lineups_generated']} total lineups")
            self.logger.info(f"Created {len(results['files_created'])} CSV files")
            
        except Exception as e:
            error_msg = f"Pipeline failed: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
        
        return results


async def main():
    """Main function to run the DFS pipeline."""
    pipeline = DFSPipeline()
    
    # Run pipeline for NFL (can be changed to other sports)
    results = await pipeline.run_pipeline(SportType.NFL, max_entry_fee=1.0)
    
    # Print results
    print("\n" + "="*50)
    print("DFS PIPELINE RESULTS")
    print("="*50)
    print(f"Sport: {results['sport']}")
    print(f"Contests Processed: {results['contests_processed']}")
    print(f"Total Lineups Generated: {results['total_lineups_generated']}")
    print(f"Files Created: {len(results['files_created'])}")
    
    if results['files_created']:
        print("\nGenerated Files:")
        for file in results['files_created']:
            print(f"  - {file}")
    
    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  - {error}")


if __name__ == "__main__":
    asyncio.run(main()) 