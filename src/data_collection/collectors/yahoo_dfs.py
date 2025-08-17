"""
Yahoo DFS contest information collector.

This collector scrapes Yahoo DFS to extract contest details including:
- Contest fees
- Prize structures and payout percentages
- Entry limits for multi-entry contests
- Contest types and formats
"""

import asyncio
import re
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from dataclasses import dataclass

from ..base import (
    BaseWebScrapingCollector,
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


class YahooDFSCollector(BaseWebScrapingCollector):
    """Collects contest information from Yahoo DFS."""

    def __init__(self) -> None:
        config = DataCollectionConfig(
            source_name="Yahoo DFS",
            source_type=DataSourceType.WEB_SCRAPING,
            base_url="https://sports.yahoo.com/dailyfantasy",
            rate_limit_delay=2.0,  # Be respectful to Yahoo's servers
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        super().__init__(config)

        # Yahoo DFS sport URLs
        self.sport_urls = {
            SportType.NFL: "/nfl",
            SportType.NBA: "/nba",
            SportType.MLB: "/mlb",
            SportType.NHL: "/nhl",
        }

        # Contest type patterns
        self.contest_patterns = {
            "guaranteed": r"guaranteed|gtd|gpp",
            "qualifier": r"qualifier|qual|satellite",
            "satellite": r"satellite|sat",
            "multi_entry": r"multi.?entry|max.?entries|multiple",
            "single_entry": r"single.?entry|one.?entry",
        }

    async def collect_projections(
        self, sport: SportType, game_date: Optional[date] = None
    ) -> List[Any]:
        """
        This collector doesn't collect player projections.
        Use collect_contests() instead.
        """
        raise DataCollectionError(
            "Yahoo DFS collector is for contest information only. "
            "Use collect_contests() method."
        )

    async def collect_contests(
        self,
        sport: SportType,
        game_date: Optional[date] = None,
        contest_types: Optional[List[str]] = None,
    ) -> List[YahooContest]:
        """
        Collect contest information from Yahoo DFS.

        Args:
            sport: The sport to collect contests for
            game_date: The date to collect contests for (defaults to today)
            contest_types: Filter by contest types (e.g., ["Guaranteed", "Multi Entry"])

        Returns:
            List of YahooContest objects
        """
        try:
            self.logger.info(
                f"Starting contest collection from Yahoo DFS for {sport.value}"
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

            # Look for contest information
            contests = self._extract_contests_from_page(soup, sport, game_date)

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

            # Filter for multi-entry contests only
            multi_entry_contests = [
                contest for contest in contests if contest.max_entries_per_user > 1
            ]

            self.logger.info(
                f"Found {len(multi_entry_contests)} multi-entry contests "
                f"out of {len(contests)} total contests"
            )

            return multi_entry_contests

        except Exception as e:
            raise DataCollectionError(f"Failed to collect contests from Yahoo DFS: {e}")

    def _extract_contests_from_page(
        self, soup: Any, sport: SportType, game_date: Optional[date]
    ) -> List[YahooContest]:
        """Extract contest information from the page HTML."""
        contests = []

        try:
            # Look for contest containers
            # Yahoo DFS typically uses specific CSS classes or data attributes
            contest_containers = self._find_contest_containers(soup)

            for container in contest_containers:
                try:
                    contest = self._parse_contest_container(container, sport, game_date)
                    if contest:
                        contests.append(contest)
                except Exception as e:
                    self.logger.warning(f"Failed to parse contest container: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Failed to extract contests: {e}")

        return contests

    def _find_contest_containers(self, soup: Any) -> List[Any]:
        """Find contest containers in the HTML."""
        containers = []

        # Method 1: Look for common contest container patterns
        selectors = [
            '[class*="contest"]',
            '[class*="tournament"]',
            '[class*="game"]',
            '[data-testid*="contest"]',
            '[data-testid*="tournament"]',
        ]

        for selector in selectors:
            containers.extend(soup.select(selector))

        # Method 2: Look for elements with contest-related text
        for element in soup.find_all(text=re.compile(r"contest|tournament|game", re.I)):
            if element.parent:
                containers.append(element.parent)

        # Method 3: Look for table rows or list items containing contest info
        for element in soup.find_all(["tr", "li", "div"]):
            text = element.get_text().lower()
            if any(word in text for word in ["entry fee", "prize pool", "max entries"]):
                containers.append(element)

        return containers

    def _parse_contest_container(
        self, container: Any, sport: SportType, game_date: Optional[date]
    ) -> Optional[YahooContest]:
        """Parse a single contest container into a YahooContest object."""
        try:
            text = container.get_text()

            # Extract contest ID
            contest_id = self._extract_contest_id(container)

            # Extract contest name
            contest_name = self._extract_contest_name(container)

            # Extract entry fee
            entry_fee = self._extract_entry_fee(text)

            # Extract prize pool
            prize_pool = self._extract_prize_pool(text)

            # Extract entry limits
            max_entries, max_entries_per_user = self._extract_entry_limits(text)

            # Determine contest type
            contest_type = self._determine_contest_type(text)

            # Determine entry limit type
            entry_limit_type = self._determine_entry_limit_type(max_entries_per_user)

            # Determine contest characteristics
            guaranteed = bool(
                re.search(self.contest_patterns["guaranteed"], text, re.I)
            )
            qualifier = bool(re.search(self.contest_patterns["qualifier"], text, re.I))
            satellite = bool(re.search(self.contest_patterns["satellite"], text, re.I))
            gpp = guaranteed  # Guaranteed Prize Pool

            # Create contest object
            contest = YahooContest(
                contest_id=contest_id,
                contest_name=contest_name,
                sport=sport,
                contest_date=game_date or date.today(),
                entry_fee=entry_fee,
                total_prize_pool=prize_pool,
                max_entries=max_entries,
                max_entries_per_user=max_entries_per_user,
                contest_type=contest_type,
                entry_limit_type=entry_limit_type,
                guaranteed=guaranteed,
                qualifier=qualifier,
                satellite=satellite,
                gpp=gpp,
                last_updated=datetime.now(),
            )

            return contest

        except Exception as e:
            self.logger.warning(f"Failed to parse contest: {e}")
            return None

    def _extract_contest_id(self, container: Any) -> str:
        """Extract contest ID from container."""
        # Look for various ID patterns
        id_patterns = [
            r"contest[_-]?(\d+)",
            r"tournament[_-]?(\d+)",
            r"game[_-]?(\d+)",
            r"id[_-]?(\d+)",
        ]

        text = container.get_text()
        for pattern in id_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return f"yahoo_{match.group(1)}"

        # Fallback: generate ID from text hash
        import hashlib

        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"yahoo_{text_hash}"

    def _extract_contest_name(self, container: Any) -> str:
        """Extract contest name from container."""
        # Look for heading elements
        for heading in container.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            name = heading.get_text().strip()
            if isinstance(name, str) and name and len(name) > 3:
                return name

        # Look for elements with contest-related classes
        for element in container.find_all(class_=re.compile(r"name|title|contest")):
            name = element.get_text().strip()
            if isinstance(name, str) and name and len(name) > 3:
                return name

        # Fallback: use first meaningful text
        text = container.get_text().strip()
        if isinstance(text, str):
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            for line in lines:
                if len(line) > 3 and not re.match(r"^\d+$", line):
                    return line

        return "Unknown Contest"

    def _extract_entry_fee(self, text: str) -> float:
        """Extract entry fee from text."""
        # Look for dollar amounts
        fee_patterns = [
            r"\$(\d+(?:\.\d{2})?)",
            r"entry[:\s]+(\d+(?:\.\d{2})?)",
            r"fee[:\s]+(\d+(?:\.\d{2})?)",
        ]

        for pattern in fee_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue

        return 0.0

    def _extract_prize_pool(self, text: str) -> float:
        """Extract total prize pool from text."""
        # Look for dollar amounts that could be prize pools
        pool_patterns = [
            r"prize[:\s]+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"pool[:\s]+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"guaranteed[:\s]+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:prize|pool)",
        ]

        for pattern in pool_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    # Remove commas and convert to float
                    amount_str = match.group(1).replace(",", "")
                    return float(amount_str)
                except ValueError:
                    continue

        return 0.0

    def _extract_entry_limits(self, text: str) -> tuple[int, int]:
        """Extract entry limits from text."""
        # Look for entry limit patterns
        limit_patterns = [
            r"max[:\s]+(\d+)\s*entries?",
            r"limit[:\s]+(\d+)\s*entries?",
            r"entries?[:\s]+(\d+)",
            r"(\d+)\s*entries?",
        ]

        max_entries = 1000  # Default
        max_entries_per_user = 1  # Default

        for pattern in limit_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    limit = int(match.group(1))
                    if limit > 0:
                        max_entries = limit
                        max_entries_per_user = limit
                        break
                except ValueError:
                    continue

        return max_entries, max_entries_per_user

    def _determine_contest_type(self, text: str) -> str:
        """Determine the type of contest."""
        text_lower = text.lower()

        if re.search(self.contest_patterns["guaranteed"], text_lower):
            return "Guaranteed"
        elif re.search(self.contest_patterns["qualifier"], text_lower):
            return "Qualifier"
        elif re.search(self.contest_patterns["satellite"], text_lower):
            return "Satellite"
        else:
            return "Standard"

    def _determine_entry_limit_type(self, max_entries_per_user: int) -> str:
        """Determine the entry limit type."""
        if max_entries_per_user == 1:
            return "Single Entry"
        elif max_entries_per_user > 1:
            return "Multi Entry"
        else:
            return "Unknown"

    async def get_available_sports(self) -> List[SportType]:
        """Yahoo DFS supports all major sports."""
        return list(self.sport_urls.keys())

    async def get_available_dates(self, sport: SportType) -> List[date]:
        """Get available contest dates from the website."""
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

    def get_contest_statistics(self, contests: List[YahooContest]) -> Dict[str, Any]:
        """Get statistics about the collected contests."""
        if not contests:
            return {}

        stats: Dict[str, Any] = {
            "total_contests": len(contests),
            "total_prize_pool": sum(c.total_prize_pool for c in contests),
            "average_entry_fee": sum(c.entry_fee for c in contests) / len(contests),
            "contest_types": {},
            "entry_limit_types": {},
            "sports": {},
        }

        # Count contest types
        for contest in contests:
            contest_type = contest.contest_type
            if isinstance(stats["contest_types"], dict):
                stats["contest_types"][contest_type] = (
                    stats["contest_types"].get(contest_type, 0) + 1
                )

        # Count entry limit types
        for contest in contests:
            entry_type = contest.entry_limit_type
            if isinstance(stats["entry_limit_types"], dict):
                stats["entry_limit_types"][entry_type] = (
                    stats["entry_limit_types"].get(entry_type, 0) + 1
                )

        # Count sports
        for contest in contests:
            sport = contest.sport.value
            if isinstance(stats["sports"], dict):
                stats["sports"][sport] = stats["sports"].get(sport, 0) + 1

        return stats
