"""
Daily Fantasy Fuel data collector.

This collector scrapes the Daily Fantasy Fuel website to automatically
download player projections and convert them to our PlayerProjection format.
"""

import asyncio
import csv
import io
import re
import time
from typing import List, Optional, Dict, Any, Sequence
from datetime import date, datetime
from pathlib import Path
import tempfile
import os

from ..base import (
    BaseWebScrapingCollector,
    DataCollectionConfig,
    DataSourceType,
    SportType,
    PlayerProjection,
    DataCollectionError,
)


class DailyFantasyFuelCollector(BaseWebScrapingCollector):
    """Collects DFS projections by scraping Daily Fantasy Fuel website."""

    def __init__(self) -> None:
        config = DataCollectionConfig(
            source_name="Daily Fantasy Fuel",
            source_type=DataSourceType.WEB_SCRAPING,
            base_url="https://www.dailyfantasyfuel.com",
            rate_limit_delay=3.0,  # Be respectful to their servers
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        super().__init__(config)

        # Mapping of Daily Fantasy Fuel sport names to our SportType enum
        self.sport_mapping = {
            "NFL": SportType.NFL,
            "NBA": SportType.NBA,
            "MLB": SportType.MLB,
            "NHL": SportType.NHL,
            "WNBA": SportType.SOCCER,  # Using SOCCER as closest match
        }

        # URL patterns for different sports
        self.sport_urls = {
            SportType.NFL: "/nfl/dfs-lineup-tools",
            SportType.NBA: "/nba/dfs-lineup-tools",
            SportType.MLB: "/mlb/dfs-lineup-tools",
            SportType.NHL: "/nhl/dfs-lineup-tools",
        }

        # Expected CSV columns for different sports
        self.expected_columns = {
            SportType.NFL: [
                "Player",
                "Team",
                "Opponent",
                "Position",
                "Salary",
                "Projected_Points",
                "Value",
                "Game_Date",
                "Injury_Status",
            ],
            SportType.NBA: [
                "Player",
                "Team",
                "Opponent",
                "Position",
                "Salary",
                "Projected_Points",
                "Value",
                "Game_Date",
                "Injury_Status",
            ],
            SportType.MLB: [
                "Player",
                "Team",
                "Opponent",
                "Position",
                "Salary",
                "Projected_Points",
                "Value",
                "Game_Date",
                "Starting_Lineup",
            ],
            SportType.NHL: [
                "Player",
                "Team",
                "Opponent",
                "Position",
                "Salary",
                "Projected_Points",
                "Value",
                "Game_Date",
                "Starting_Lineup",
            ],
        }

    async def collect_projections(
        self, sport: SportType, game_date: Optional[date] = None
    ) -> List[PlayerProjection]:
        """
        Collect projections by scraping Daily Fantasy Fuel website.

        This method will:
        1. Navigate to the appropriate sport page
        2. Look for CSV download links
        3. Download and parse the CSV data
        4. Convert to PlayerProjection objects
        """
        try:
            self.logger.info(
                f"Starting collection from Daily Fantasy Fuel for {sport.value}"
            )

            # Get the sport-specific URL
            sport_url = self.sport_urls.get(sport)
            if not sport_url:
                raise DataCollectionError(f"Unsupported sport: {sport.value}")

            # Navigate to the sport page
            full_url = f"{self.config.base_url}{sport_url}"
            self.logger.info(f"Navigating to: {full_url}")

            html_content = await self._get_page_content(full_url)
            soup = await self._parse_html(html_content)

            # Look for CSV download links
            csv_links = self._find_csv_download_links(soup, sport)

            if not csv_links:
                raise DataCollectionError(
                    f"No CSV download links found for {sport.value} on Daily Fantasy Fuel"
                )

            # Download and process the first available CSV
            csv_url = csv_links[0]
            self.logger.info(f"Downloading CSV from: {csv_url}")

            csv_content = await self._download_csv(csv_url)
            if not csv_content:
                raise DataCollectionError("Failed to download CSV content")

            # Parse the CSV content
            projections = self._parse_csv_content(csv_content, sport, game_date)

            self.logger.info(
                f"Successfully collected {len(projections)} projections from Daily Fantasy Fuel"
            )
            return projections

        except Exception as e:
            raise DataCollectionError(f"Failed to collect from Daily Fantasy Fuel: {e}")

    def _find_csv_download_links(self, soup: Any, sport: SportType) -> List[str]:
        """Find CSV download links on the page."""
        csv_links = []

        # Look for various types of download links
        # Method 1: Look for links with "csv" in href or text
        for link in soup.find_all("a", href=True):
            href = link.get("href", "").lower()
            text = link.get_text().lower()

            if "csv" in href or "csv" in text or "download" in text:
                if href.startswith("http"):
                    csv_links.append(href)
                elif href.startswith("/"):
                    csv_links.append(f"{self.config.base_url}{href}")
                else:
                    csv_links.append(f"{self.config.base_url}/{href}")

        # Method 2: Look for buttons with download functionality
        for button in soup.find_all(
            ["button", "a"], class_=re.compile(r"download|csv|export")
        ):
            onclick = button.get("onclick", "")
            if "csv" in onclick.lower() or "download" in onclick.lower():
                # Extract URL from onclick attribute
                url_match = re.search(r'["\']([^"\']*\.csv)["\']', onclick)
                if url_match:
                    url = url_match.group(1)
                    if url.startswith("http"):
                        csv_links.append(url)
                    else:
                        csv_links.append(f"{self.config.base_url}/{url}")

        # Method 3: Look for data attributes that might contain download URLs
        for element in soup.find_all(attrs={"data-download-url": True}):
            url = element.get("data-download-url")
            if url and "csv" in url.lower():
                if url.startswith("http"):
                    csv_links.append(url)
                else:
                    csv_links.append(f"{self.config.base_url}/{url}")

        self.logger.info(f"Found {len(csv_links)} potential CSV download links")
        return csv_links

    async def _download_csv(self, csv_url: str) -> Optional[str]:
        """Download CSV content from the given URL."""
        try:
            # Add delay to be respectful
            await asyncio.sleep(self.config.rate_limit_delay)

            # Download the CSV content
            if self.session is None:
                raise DataCollectionError("Session not initialized")

            async with self.session.get(csv_url) as response:
                response.raise_for_status()
                content = await response.text()

                # Verify it looks like CSV content
                if isinstance(content, str) and "," in content and "\n" in content:
                    return content
                else:
                    self.logger.warning("Downloaded content doesn't appear to be CSV")
                    return None

        except Exception as e:
            self.logger.error(f"Failed to download CSV from {csv_url}: {e}")
            return None

    def _parse_csv_content(
        self, csv_content: str, sport: SportType, game_date: Optional[date]
    ) -> List[PlayerProjection]:
        """Parse CSV content and convert to PlayerProjection objects."""
        try:
            projections = []

            # Parse CSV content
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)

            # Validate columns
            if not self._validate_csv_columns(reader.fieldnames, sport):
                self.logger.warning(
                    f"CSV columns don't match expected format for {sport.value}. "
                    f"Found: {reader.fieldnames}"
                )

            # Process each row
            for row in reader:
                try:
                    projection = self._parse_csv_row(row, sport, game_date)
                    if projection:
                        projections.append(projection)
                except Exception as e:
                    self.logger.warning(f"Failed to parse row: {e}")
                    continue

            return projections

        except Exception as e:
            raise DataCollectionError(f"Failed to parse CSV content: {e}")

    def _validate_csv_columns(
        self, fieldnames: Optional[Sequence[str]], sport: SportType
    ) -> bool:
        """Validate that CSV has expected columns for the sport."""
        if not fieldnames:
            return False

        expected = self.expected_columns.get(sport, [])
        if not expected:
            return True  # No validation for unknown sports

        # Check if required columns are present
        required_cols = ["Player", "Team", "Position"]
        return all(col in fieldnames for col in required_cols)

    def _parse_csv_row(
        self, row: Dict[str, str], sport: SportType, game_date: Optional[date]
    ) -> Optional[PlayerProjection]:
        """Parse a single CSV row into a PlayerProjection."""
        try:
            # Extract basic player info
            player_name = row.get("Player", "").strip()
            if not player_name:
                return None

            team = row.get("Team", "").strip()
            opponent = row.get("Opponent", "").strip()
            position = row.get("Position", "").strip()

            # Extract salary
            salary_str = row.get("Salary", "").strip()
            salary = None
            if salary_str:
                try:
                    # Remove currency symbols and commas
                    salary = int(salary_str.replace("$", "").replace(",", ""))
                except ValueError:
                    self.logger.warning(f"Invalid salary format: {salary_str}")

            # Extract projected points
            points_str = row.get("Projected_Points", "").strip()
            projected_points = None
            if points_str:
                try:
                    projected_points = float(points_str)
                except ValueError:
                    self.logger.warning(f"Invalid points format: {points_str}")

            # Calculate value (points per dollar)
            projected_value = None
            if projected_points and salary and salary > 0:
                projected_value = round(projected_points / salary, 4)

            # Extract game date
            game_date_str = row.get("Game_Date", "").strip()
            parsed_game_date = game_date
            if game_date_str:
                try:
                    # Try different date formats
                    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"]:
                        try:
                            parsed_game_date = datetime.strptime(
                                game_date_str, fmt
                            ).date()
                            break
                        except ValueError:
                            continue
                except Exception:
                    self.logger.warning(f"Could not parse game date: {game_date_str}")

            # Extract additional info
            injury_status = row.get("Injury_Status", "").strip() or None

            # Create projection
            projection = PlayerProjection(
                player_id=f"dff_{player_name.lower().replace(' ', '_').replace('.', '')}",
                player_name=player_name,
                team=team,
                opponent=opponent,
                position=position,
                salary=salary,
                projected_points=projected_points,
                projected_value=projected_value,
                game_date=parsed_game_date,
                source=self.config.source_name,
                last_updated=datetime.now(),
                confidence=0.8,  # Daily Fantasy Fuel projections are generally reliable
                injury_status=injury_status,
            )

            return projection

        except Exception as e:
            self.logger.warning(f"Failed to parse row {row}: {e}")
            return None

    async def get_available_sports(self) -> List[SportType]:
        """Daily Fantasy Fuel supports all major sports."""
        return list(self.sport_mapping.values())

    async def get_available_dates(self, sport: SportType) -> List[date]:
        """Get available dates from the website."""
        try:
            # Navigate to the sport page to see available dates
            sport_url = self.sport_urls.get(sport)
            if not sport_url:
                return []

            full_url = f"{self.config.base_url}{sport_url}"
            html_content = await self._get_page_content(full_url)
            soup = await self._parse_html(html_content)

            # Look for date information on the page
            dates = []

            # Look for date elements
            for date_elem in soup.find_all(text=re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")):
                try:
                    # Extract date from text
                    date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", date_elem)
                    if date_match:
                        date_str = date_match.group(1)
                        parsed_date = datetime.strptime(date_str, "%m/%d/%Y").date()
                        dates.append(parsed_date)
                except Exception:
                    continue

            # If no dates found, return today
            if not dates:
                dates = [date.today()]

            return dates

        except Exception as e:
            self.logger.error(f"Failed to get available dates: {e}")
            return [date.today()]

    def get_supported_platforms(self) -> List[str]:
        """Get list of supported DFS platforms."""
        return ["DraftKings", "FanDuel"]

    def get_sport_mapping(self) -> Dict[str, SportType]:
        """Get mapping of Daily Fantasy Fuel sport names to our SportType enum."""
        return self.sport_mapping.copy()

    async def login_if_required(self, username: str, password: str) -> bool:
        """
        Attempt to log in to Daily Fantasy Fuel if required.

        Note: This is a placeholder for premium content access.
        Daily Fantasy Fuel may require authentication for CSV downloads.
        """
        try:
            # Look for login form
            login_url = f"{self.config.base_url}/login"
            html_content = await self._get_page_content(login_url)
            soup = await self._parse_html(html_content)

            # Find login form
            login_form = soup.find("form")
            if not login_form:
                self.logger.warning("No login form found")
                return False

            # This would need to be implemented based on the actual login form
            # For now, just log that login would be required
            self.logger.info(
                "Login form found - authentication may be required for CSV downloads"
            )
            return False

        except Exception as e:
            self.logger.error(f"Failed to check login requirements: {e}")
            return False
