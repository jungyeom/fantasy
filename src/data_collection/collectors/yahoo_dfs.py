"""
Yahoo DFS contest information collector.

This collector uses the Yahoo DFS API to extract contest details including:
- Contest fees
- Prize structures and payout percentages
- Entry limits for multi-entry contests
- Contest types and formats
"""

import asyncio
import json
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from dataclasses import dataclass
import re

from ..base import (
    BaseAPICollector,
    DataCollectionConfig,
    DataSourceType,
    SportType,
    DataCollectionError,
)


@dataclass
class YahooContest:
    """Data structure for Yahoo DFS contest information."""

    contest_id: str
    contest_name: str
    sport: SportType
    contest_date: Optional[date]
    entry_fee: float
    total_prize_pool: float
    max_entries: int
    max_entries_per_user: int
    slate_type: str = "UNKNOWN"
    salary_cap: int = 0
    source: str = "Yahoo DFS"
    last_updated: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate data after initialization."""
        if self.entry_fee < 0:
            raise ValueError("Entry fee cannot be negative")
        if self.total_prize_pool < 0:
            raise ValueError("Total prize pool cannot be negative")
        if self.max_entries <= 0:
            raise ValueError("Max entries must be positive")
        if self.max_entries_per_user <= 0:
            raise ValueError("Max entries per user must be positive")


class YahooDFSCollector(BaseAPICollector):
    """Collects contest information from Yahoo DFS using their API."""

    def __init__(self) -> None:
        config = DataCollectionConfig(
            source_name="Yahoo DFS",
            source_type=DataSourceType.API,
            base_url="https://dfyql-ro.sports.yahoo.com/v2",
            rate_limit_delay=1.0,  # Be respectful to Yahoo's API
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        super().__init__(config)

        # Yahoo DFS sport codes
        self.sport_codes = {
            SportType.NFL: "nfl",
            SportType.NBA: "nba", 
            SportType.MLB: "mlb",
            SportType.NHL: "nhl",
        }

    async def collect_contests(
        self, 
        sport: SportType, 
        game_date: Optional[date] = None,
        contest_types: Optional[List[str]] = None,
        multi_entry_only: bool = True,
    ) -> List[YahooContest]:
        """
        Collect contest information from Yahoo DFS API.
        
        Args:
            sport: The sport to collect contests for
            game_date: The date to collect contests for (not used in current API)
            contest_types: Filter by contest types (e.g., ["Guaranteed", "Multi Entry"])
            multi_entry_only: Whether to only return multi-entry contests
            
        Returns:
            List of YahooContest objects
        """
        try:
            self.logger.info(
                f"Starting contest collection from Yahoo DFS API for {sport.value}"
            )

            # Get the sport code
            sport_code = self.sport_codes.get(sport)
            if not sport_code:
                raise DataCollectionError(f"Unsupported sport: {sport.value}")

            # Add slateTypes parameter to get both single game and multi game contests
            endpoint = f"contestsFilteredWeb?sport={sport_code}&slateTypes=SINGLE_GAME&slateTypes=MULTI_GAME"
            self.logger.info(f"Requesting endpoint: {endpoint}")
            
            response = await self._make_request(endpoint)
            if not response:
                raise DataCollectionError("No response from Yahoo DFS API")

            # Parse the response
            contests = self._parse_api_response(response)
            self.logger.info(f"Found {len(contests)} total contests")

            # Filter by contest types if specified
            if contest_types:
                contests = [
                    contest
                    for contest in contests
                    if any(
                        ct.lower() in contest.contest_type.lower()
                        for ct in contest_types
                    )
                ]

            # Filter for multi-entry contests only if requested
            if multi_entry_only:
                contests = [
                    contest for contest in contests 
                    if contest.max_entries_per_user > 1
                ]

            self.logger.info(
                f"Returning {len(contests)} contests "
                f"({'multi-entry only' if multi_entry_only else 'all types'})"
            )

            return contests

        except Exception as e:
            raise DataCollectionError(f"Failed to collect contests from Yahoo DFS: {e}")

    def _parse_api_response(self, response: Dict[str, Any]) -> List[YahooContest]:
        """Parse the API response to extract contest information."""
        try:
            contests = []
            
            # Handle nested structure: response['contests']['result']
            if 'contests' in response and 'result' in response['contests']:
                contests_data = response['contests']['result']
            else:
                self.logger.warning("No contests found in API response")
                return []
            
            for contest_data in contests_data:
                try:
                    contest = self._parse_contest_data(contest_data)
                    if contest:
                        contests.append(contest)
                except Exception as e:
                    self.logger.warning(f"Failed to parse contest: {e}")
                    continue
            
            return contests
            
        except Exception as e:
            self.logger.error(f"Failed to parse API response: {e}")
            return []

    def _parse_contest_data(self, contest_data: Dict[str, Any]) -> Optional[YahooContest]:
        """Parse individual contest data from the API response."""
        try:
            # Extract basic contest information
            contest_id = str(contest_data.get("id", ""))
            contest_name = contest_data.get("title", "")
            
            # Handle nested monetary values
            entry_fee_data = contest_data.get("paidEntryFee", {})
            if isinstance(entry_fee_data, dict):
                entry_fee = entry_fee_data.get("value", 0)
            else:
                entry_fee = entry_fee_data
            
            total_prize_pool_data = contest_data.get("paidTotalPrize", {})
            if isinstance(total_prize_pool_data, dict):
                total_prize_pool = total_prize_pool_data.get("value", 0)
            else:
                total_prize_pool = total_prize_pool_data
            
            max_entries = contest_data.get("entryLimit", 0)
            max_entries_per_user = contest_data.get("multipleEntryLimit", 1)
            start_time = contest_data.get("startTime", "")
            slate_type = contest_data.get("slateType", "UNKNOWN")
            salary_cap = contest_data.get("salaryCap", 0)
            
            # Extract sport from contest data
            sport_code = contest_data.get("sportCode", "nfl")
            sport = self._get_sport_type(sport_code)
            
            # Parse start time to get contest date
            contest_date = self._parse_start_time(start_time) if start_time else None
            
            # Create YahooContest object
            contest = YahooContest(
                contest_id=contest_id,
                contest_name=contest_name,
                sport=sport,
                contest_date=contest_date,
                entry_fee=float(entry_fee),
                total_prize_pool=float(total_prize_pool),
                max_entries=int(max_entries),
                max_entries_per_user=int(max_entries_per_user),
                slate_type=slate_type,
                salary_cap=int(salary_cap)
            )
            
            return contest
            
        except Exception as e:
            self.logger.warning(f"Failed to parse contest data: {e}")
            return None
    
    def _parse_start_time(self, start_time: str) -> Optional[date]:
        """Parse start time string to date."""
        try:
            if start_time:
                # Convert milliseconds timestamp to date
                timestamp_ms = int(start_time)
                return datetime.fromtimestamp(timestamp_ms / 1000).date()
            return None
        except (ValueError, TypeError):
            return None
    
    def _get_sport_type(self, sport_code: str) -> SportType:
        """Convert sport code to SportType enum."""
        sport_mapping = {
            'nfl': SportType.NFL,
            'nba': SportType.NBA,
            'mlb': SportType.MLB,
            'nhl': SportType.NHL
        }
        return sport_mapping.get(sport_code.lower(), SportType.NFL)

    def _determine_contest_type(self, contest_data: Dict[str, Any]) -> str:
        """Determine the contest type from the data."""
        contest_name = contest_data.get("title", "").lower()
        contest_type = contest_data.get("type", "")
        
        if "guaranteed" in contest_name:
            return "Guaranteed"
        elif "qualifier" in contest_name:
            return "Qualifier"
        elif "satellite" in contest_name:
            return "Satellite"
        elif contest_type == "50-50":
            return "50/50"
        elif contest_type == "head2head":
            return "Head-to-Head"
        elif contest_type == "league":
            return "League"
        else:
            return contest_type.title() if contest_type else "Standard"

    def _determine_entry_limit_type(self, contest_data: Dict[str, Any]) -> str:
        """Determine the entry limit type from the data."""
        multiple_entry = contest_data.get("multipleEntry", False)
        multiple_entry_limit = contest_data.get("multipleEntryLimit", 1)
        
        if multiple_entry_limit == 1:
            return "Single Entry"
        elif multiple_entry_limit > 1:
            return f"Multi Entry (Max {multiple_entry_limit})"
        elif multiple_entry:
            return "Multiple Entry"
        else:
            return "Single Entry"

    async def collect_projections(
        self, sport: SportType, game_date: Optional[date] = None
    ) -> List[Any]:
        """
        This collector doesn't collect player projections.
        Use collect_contests() instead.
        """
        raise DataCollectionError(
            "Yahoo DFS collector only collects contest information, not player projections"
        )

    async def get_contest_players(self, contest_id: str) -> List[Dict[str, Any]]:
        """
        Fetch player information for a specific contest.

        Args:
            contest_id: The Yahoo contest ID

        Returns:
            List of player dictionaries with ID, name, team, position, salary, etc.
        """
        try:
            endpoint = f"export/contestPlayers?contestId={contest_id}"
            self.logger.info(f"Fetching players for contest {contest_id}")

            # This endpoint returns CSV, so we need to make a direct request
            url = f"https://dfyql-ro.sports.yahoo.com/v2/{endpoint}"

            if not self.session:
                import aiohttp
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    headers=self.config.headers or {},
                )

            async with self.session.get(url) as response:
                if response.status == 200:
                    csv_content = await response.text()
                    players = self._parse_csv_players(csv_content)
                    self.logger.info(f"Found {len(players)} players for contest {contest_id}")
                    return players
                else:
                    self.logger.error(f"Failed to fetch players: {response.status}")
                    return []

        except Exception as e:
            self.logger.error(f"Failed to fetch players for contest {contest_id}: {e}")
            return []

    def _parse_csv_players(self, csv_content: str) -> List[Dict[str, Any]]:
        """Parse CSV content from the contest players endpoint."""
        try:
            import csv
            from io import StringIO
            
            players = []
            csv_file = StringIO(csv_content)
            csv_reader = csv.DictReader(csv_file)
            
            for row in csv_reader:
                # Convert row to dict and clean up values
                player = {}
                for key, value in row.items():
                    if value and value.strip():
                        # Try to convert numeric values
                        try:
                            if '.' in value:
                                player[key] = float(value)
                            else:
                                player[key] = int(value)
                        except ValueError:
                            player[key] = value.strip()
                    else:
                        player[key] = None
                
                # Construct full name from First Name and Last Name
                first_name = player.get('First Name', '')
                last_name = player.get('Last Name', '')
                if first_name and last_name:
                    player['name'] = f"{first_name} {last_name}"
                
                players.append(player)
            
            return players

        except Exception as e:
            self.logger.error(f"Failed to parse CSV players: {e}")
            return []

    async def get_contest_game_info(self, contest_id: str) -> Dict[str, Any]:
        """
        Fetch game information for a specific contest.

        Args:
            contest_id: The Yahoo contest ID

        Returns:
            Dictionary containing game information including game ID
        """
        try:
            # First get the contest details to find the game
            contests = await self.collect_contests(SportType.NFL, multi_entry_only=False)
            contest = next((c for c in contests if c.contest_id == contest_id), None)
            
            if not contest:
                self.logger.error(f"Contest {contest_id} not found")
                return {}
            
            # Extract game information from contest data
            # This is a placeholder - actual implementation depends on Yahoo's API structure
            game_info = {
                "contest_id": contest_id,
                "game_id": f"nfl.g.{contest_id}",  # Placeholder format
                "sport": "nfl",
                "game_time": getattr(contest, 'start_time', None),
                "teams": [],  # Will be populated from player data
            }
            
            # Get players to extract team information
            players = await self.get_contest_players(contest_id)
            teams = set()
            for player in players:
                if player.get('team'):
                    teams.add(player['team'])
            
            game_info['teams'] = list(teams)
            
            return game_info

        except Exception as e:
            self.logger.error(f"Failed to fetch game info for contest {contest_id}: {e}")
            return {}

    async def get_players_with_ids(self, contest_id: str) -> List[Dict[str, Any]]:
        """
        Fetch players with their Yahoo player IDs and game IDs.

        Args:
            contest_id: The Yahoo contest ID

        Returns:
            List of player dictionaries with Yahoo IDs and game information
        """
        try:
            # Get basic player information
            players = await self.get_contest_players(contest_id)
            
            # Get game information
            game_info = await self.get_contest_game_info(contest_id)
            
            # Enhance player data with IDs
            enhanced_players = []
            for player in players:
                # Use the actual Yahoo player ID from the CSV
                yahoo_player_id = player.get('ID', '')
                
                # Extract game ID from the Game field (e.g., "DAL@PHI" -> generate game ID)
                game_field = player.get('Game', '')
                if game_field and '@' in game_field:
                    # Generate a game ID based on the teams and contest
                    game_id = f"nfl.g.{hash(game_field + contest_id) % 100000000}"
                else:
                    game_id = f"nfl.g.{contest_id}"
                
                enhanced_player = player.copy()
                enhanced_player.update({
                    'yahoo_player_id': yahoo_player_id,
                    'game_id': game_id,
                    'full_yahoo_id': f"{game_id}${yahoo_player_id}",
                    'sport': 'nfl',
                })
                enhanced_players.append(enhanced_player)
            
            self.logger.info(f"Enhanced {len(enhanced_players)} players with Yahoo IDs")
            return enhanced_players

        except Exception as e:
            self.logger.error(f"Failed to get players with IDs for contest {contest_id}: {e}")
            return []

    async def get_standardized_players(self, contest_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get players for a contest with standardized names and Yahoo IDs.

        Args:
            contest_id: The Yahoo contest ID

        Returns:
            Dictionary mapping standardized player names to their data
        """
        players = await self.get_players_with_ids(contest_id)
        
        standardized = {}
        for player in players:
            name = self._standardize_name(player.get("name", ""))
            if name:
                standardized[name] = player
        
        return standardized

    def _standardize_name(self, name: str) -> str:
        """Standardize player name to Yahoo format."""
        if not name:
            return ""
        return re.sub(r'\s+', ' ', name.strip()).lower()

    def get_available_sports(self) -> List[SportType]:
        """Get list of available sports."""
        return list(self.sport_codes.keys())

    def get_available_dates(self, sport: SportType) -> List[date]:
        """Get available dates for a sport (not applicable for current API)."""
        return [date.today()]

    def get_contest_statistics(self, contests: List[YahooContest]) -> Dict[str, Any]:
        """Get statistics about the collected contests."""
        if not contests:
            return {}
        
        total_contests = len(contests)
        total_prize_pools = sum(c.total_prize_pool for c in contests)
        total_entry_fees = sum(c.entry_fee for c in contests)
        
        # Entry fee distribution
        entry_fee_ranges = {
            "$1-5": len([c for c in contests if 1 <= c.entry_fee <= 5]),
            "$6-20": len([c for c in contests if 6 <= c.entry_fee <= 20]),
            "$21-100": len([c for c in contests if 21 <= c.entry_fee <= 100]),
            "$101+": len([c for c in contests if c.entry_fee > 100]),
        }
        
        # Contest type distribution
        contest_types = {}
        for contest in contests:
            contest_type = contest.contest_type
            contest_types[contest_type] = contest_types.get(contest_type, 0) + 1
        
        # Multi-entry vs single-entry
        multi_entry_count = len([c for c in contests if c.max_entries_per_user > 1])
        single_entry_count = total_contests - multi_entry_count
        
        return {
            "total_contests": total_contests,
            "total_prize_pools": total_prize_pools,
            "total_entry_fees": total_entry_fees,
            "average_prize_pool": total_prize_pools / total_contests if total_contests > 0 else 0,
            "average_entry_fee": total_entry_fees / total_contests if total_contests > 0 else 0,
            "entry_fee_distribution": entry_fee_ranges,
            "contest_type_distribution": contest_types,
            "multi_entry_count": multi_entry_count,
            "single_entry_count": single_entry_count,
            "multi_entry_percentage": (multi_entry_count / total_contests * 100) if total_contests > 0 else 0,
        }
