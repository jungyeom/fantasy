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
    contest_date: date
    entry_fee: float
    total_prize_pool: float
    max_entries: int
    max_entries_per_user: int
    contest_type: str  # e.g., "Guaranteed", "Qualifier", "Satellite"
    entry_limit_type: str  # "Single Entry", "Multi Entry", "Max Entries"
    guaranteed: bool
    qualifier: bool
    satellite: bool
    gpp: bool  # Guaranteed Prize Pool
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

            # Make API request
            endpoint = f"contestsFilteredWeb?sport={sport_code}"
            self.logger.info(f"Requesting endpoint: {endpoint}")
            
            response = await self._make_request(endpoint)
            if not response:
                raise DataCollectionError("No response from Yahoo DFS API")

            # Parse the response
            contests = self._parse_api_response(response, sport)
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

    def _parse_api_response(self, response: Dict[str, Any], sport: SportType) -> List[YahooContest]:
        """Parse the API response and extract contest information."""
        try:
            if "contests" not in response or "result" not in response["contests"]:
                self.logger.warning("No contests data in API response")
                return []
            
            contests = []
            for contest_data in response["contests"]["result"]:
                try:
                    contest = self._parse_contest_data(contest_data, sport)
                    if contest:
                        contests.append(contest)
                except Exception as e:
                    self.logger.warning(f"Failed to parse contest: {e}")
                    continue
            
            return contests
            
        except Exception as e:
            self.logger.error(f"Failed to parse API response: {e}")
            return []

    def _parse_contest_data(self, contest_data: Dict[str, Any], sport: SportType) -> Optional[YahooContest]:
        """Parse individual contest data from the API response."""
        try:
            # Extract basic contest information
            contest_id = str(contest_data.get("id", ""))
            contest_name = contest_data.get("title", "")
            
            if not contest_id or not contest_name:
                return None
            
            # Extract entry fee and prize pool
            entry_fee = contest_data.get("paidEntryFee", {}).get("value", 0.0)
            total_prize_pool = contest_data.get("paidTotalPrize", {}).get("value", 0.0)
            
            # Extract entry limits
            max_entries = contest_data.get("entryLimit", 0)
            max_entries_per_user = contest_data.get("multipleEntryLimit", 1)
            
            # Determine contest type
            contest_type = self._determine_contest_type(contest_data)
            entry_limit_type = self._determine_entry_limit_type(contest_data)
            
            # Extract boolean flags
            guaranteed = contest_data.get("guaranteed", False)
            qualifier = "qualifier" in contest_name.lower()
            satellite = "satellite" in contest_name.lower()
            gpp = guaranteed  # Guaranteed Prize Pool
            
            # Extract start time and convert to date
            start_time_ms = contest_data.get("startTime", 0)
            if start_time_ms:
                contest_date = datetime.fromtimestamp(start_time_ms / 1000).date()
            else:
                contest_date = date.today()
            
            return YahooContest(
                contest_id=contest_id,
                contest_name=contest_name,
                sport=sport,
                contest_date=contest_date,
                entry_fee=float(entry_fee),
                total_prize_pool=float(total_prize_pool),
                max_entries=int(max_entries),
                max_entries_per_user=int(max_entries_per_user),
                contest_type=contest_type,
                entry_limit_type=entry_limit_type,
                guaranteed=guaranteed,
                qualifier=qualifier,
                satellite=satellite,
                gpp=gpp,
                last_updated=datetime.now(),
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to parse contest data: {e}")
            return None

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

    async def get_standardized_players(self, contest_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get players with standardized names for cross-source matching.
        
        Returns:
            Dict mapping standardized names to player data
        """
        players = await self.get_contest_players(contest_id)
        
        standardized = {}
        for player in players:
            name = player.get("name", "")
            if name:
                std_name = self._standardize_name(name)
                standardized[std_name] = player
        
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
