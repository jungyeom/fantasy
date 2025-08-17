"""
Basketball Reference data collector.

This collector scrapes NBA player stats and projections from Basketball Reference.
"""

from typing import List, Optional
from datetime import date, datetime
import re
from bs4 import BeautifulSoup

from ..base import (
    BaseWebScrapingCollector,
    DataCollectionConfig,
    DataSourceType,
    SportType,
    PlayerProjection,
    DataCollectionError,
)


class BasketballReferenceCollector(BaseWebScrapingCollector):
    """Collects NBA data from Basketball Reference."""

    def __init__(self) -> None:
        config = DataCollectionConfig(
            source_name="Basketball Reference",
            source_type=DataSourceType.WEB_SCRAPING,
            base_url="https://www.basketball-reference.com",
            rate_limit_delay=2.0,  # Be respectful to their servers
            user_agent="Mozilla/5.0 (compatible; DFSBot/1.0)",
        )
        super().__init__(config)

    async def collect_projections(
        self, sport: SportType, game_date: Optional[date] = None
    ) -> List[PlayerProjection]:
        """Collect NBA player projections from Basketball Reference."""
        if sport != SportType.NBA:
            raise DataCollectionError("Basketball Reference only supports NBA")

        if game_date is None:
            game_date = date.today()

        try:
            # Get the schedule page for the given date
            schedule_url = (
                f"{self.config.base_url}/leaders/pts_per_g/{game_date.year}.html"
            )
            html_content = await self._get_page_content(schedule_url)
            soup = await self._parse_html(html_content)

            projections = []

            # Find the stats table
            stats_table = soup.find("table", {"id": "nba-stats"})
            if not stats_table:
                # Try alternative table ID
                stats_table = soup.find("table", {"class": "stats_table"})

            if stats_table:
                rows = stats_table.find_all("tr")[1:]  # Skip header row

                for row in rows:
                    try:
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 8:
                            # Extract player information
                            player_name_cell = cells[1]
                            player_link = player_name_cell.find("a")
                            if player_link:
                                player_name = player_link.get_text(strip=True)
                                player_url = player_link.get("href")
                                player_id = self._extract_player_id(player_url)

                                # Extract team
                                team_cell = cells[2]
                                team = team_cell.get_text(strip=True)

                                # Extract position
                                pos_cell = cells[3]
                                position = pos_cell.get_text(strip=True)

                                # Extract points per game (as a proxy for projections)
                                ppg_cell = cells[4]
                                ppg_text = ppg_cell.get_text(strip=True)
                                try:
                                    ppg = float(ppg_text) if ppg_text else None
                                except ValueError:
                                    ppg = None

                                # Extract games played
                                games_cell = cells[5]
                                games_text = games_cell.get_text(strip=True)
                                try:
                                    games = int(games_text) if games_text else None
                                except ValueError:
                                    games = None

                                # Create projection (using season averages as proxy)
                                if ppg is not None and games is not None and games > 0:
                                    player_id_fallback = (
                                        f"br_{player_name.lower().replace(' ', '_')}"
                                    )
                                    projection = PlayerProjection(
                                        player_id=player_id or player_id_fallback,
                                        player_name=player_name,
                                        team=team,
                                        opponent="TBD",  # Would need to scrape
                                        # schedule separately
                                        position=position,
                                        projected_points=ppg,
                                        game_date=game_date,
                                        source=self.config.source_name,
                                        last_updated=datetime.now(),
                                        confidence=0.7,  # Season averages are
                                        # moderately reliable
                                    )
                                    projections.append(projection)

                    except Exception as e:
                        self.logger.warning(f"Failed to parse row: {e}")
                        continue

            self.logger.info(
                f"Collected {len(projections)} projections from Basketball Reference"
            )
            return projections

        except Exception as e:
            raise DataCollectionError(
                f"Failed to collect from Basketball Reference: {e}"
            )

    async def get_available_sports(self) -> List[SportType]:
        """Basketball Reference only supports NBA."""
        return [SportType.NBA]

    async def get_available_dates(self, sport: SportType) -> List[date]:
        """Get available dates for NBA (current season)."""
        if sport != SportType.NBA:
            return []

        try:
            # Get current year's stats page
            current_year = datetime.now().year
            url = f"{self.config.base_url}/leaders/pts_per_g/{current_year}.html"
            html_content = await self._get_page_content(url)
            soup = await self._parse_html(html_content)

            # Check if page exists and has data
            if soup.find("table", {"id": "nba-stats"}) or soup.find(
                "table", {"class": "stats_table"}
            ):
                return [date.today()]  # For now, just return today
            else:
                return []

        except Exception as e:
            self.logger.error(f"Failed to get available dates: {e}")
            return []

    def _extract_player_id(self, player_url: str) -> Optional[str]:
        """Extract player ID from Basketball Reference URL."""
        if not player_url:
            return None

        # URL format: /players/l/lebrone01.html
        match = re.search(r"/players/[a-z]/([a-z]+[0-9]+)\.html", player_url)
        if match:
            return match.group(1)
        return None

    async def get_player_details(self, player_id: str) -> Optional[dict]:
        """Get detailed player information."""
        try:
            url = f"{self.config.base_url}/players/{player_id[0]}/{player_id}.html"
            html_content = await self._get_page_content(url)
            soup = await self._parse_html(html_content)

            # Extract additional player details
            details = {}

            # Get player name
            name_elem = soup.find("h1", {"itemprop": "name"})
            if name_elem:
                details["full_name"] = name_elem.get_text(strip=True)

            # Get current team
            team_elem = soup.find("strong", text=re.compile(r"Team:"))
            if team_elem and team_elem.parent:
                team_text = team_elem.parent.get_text()
                team_match = re.search(r"Team:\s*([^\n]+)", team_text)
                if team_match:
                    details["current_team"] = team_match.group(1).strip()

            # Get position
            pos_elem = soup.find("strong", text=re.compile(r"Position:"))
            if pos_elem and pos_elem.parent:
                pos_text = pos_elem.parent.get_text()
                pos_match = re.search(r"Position:\s*([^\n]+)", pos_text)
                if pos_match:
                    details["position"] = pos_match.group(1).strip()

            return details

        except Exception as e:
            self.logger.error(f"Failed to get player details for {player_id}: {e}")
            return None
