"""
Abstract base classes for DFS data collection.

This module provides the foundation for collecting player projections from "
"various sources.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
import asyncio
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SportType(Enum):
    """Supported sports for DFS."""

    NFL = "nfl"
    NBA = "nba"
    MLB = "mlb"
    NHL = "nhl"
    SOCCER = "soccer"


class DataSourceType(Enum):
    """Types of data sources."""

    API = "api"
    WEB_SCRAPING = "web_scraping"
    FILE = "file"
    DATABASE = "database"


@dataclass
class PlayerProjection:
    """Data structure for player projections."""

    player_id: str
    player_name: str
    team: str
    opponent: str
    position: str
    salary: Optional[int] = None
    projected_points: Optional[float] = None
    projected_value: Optional[float] = None  # points per dollar
    game_date: Optional[date] = None
    game_time: Optional[str] = None
    injury_status: Optional[str] = None
    weather: Optional[str] = None
    source: Optional[str] = None
    last_updated: Optional[datetime] = None
    confidence: Optional[float] = None  # 0-1 scale for projection confidence

    def __post_init__(self) -> None:
        """Validate data after initialization."""
        if self.projected_points is not None and self.projected_points < 0:
            raise ValueError("Projected points cannot be negative")
        if self.confidence is not None and not (0 <= self.confidence <= 1):
            raise ValueError("Confidence must be between 0 and 1")


@dataclass
class DataCollectionConfig:
    """Configuration for data collection."""

    source_name: str
    source_type: DataSourceType
    base_url: str
    api_key: Optional[str] = None
    rate_limit_delay: float = 1.0  # seconds between requests
    max_retries: int = 3
    timeout: int = 30
    user_agent: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class DataCollectionError(Exception):
    """Custom exception for data collection errors."""

    pass


class BaseDataCollector(ABC):
    """
    Abstract base class for all data collectors.

    This class defines the interface that all data collectors must implement,
    providing a consistent way to collect player projections from various sources.
    """

    def __init__(self, config: DataCollectionConfig):
        self.config = config
        self.session: Optional[Any] = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def collect_projections(
        self, sport: SportType, game_date: Optional[date] = None
    ) -> List[PlayerProjection]:
        """
        Collect player projections for a given sport and date.

        Args:
            sport: The sport to collect data for
            game_date: The date to collect data for (defaults to today)

        Returns:
            List of PlayerProjection objects

        Raises:
            DataCollectionError: If data collection fails
        """
        pass

    @abstractmethod
    async def get_available_sports(self) -> List[SportType]:
        """Get list of sports supported by this data source."""
        pass

    @abstractmethod
    async def get_available_dates(self, sport: SportType) -> List[date]:
        """Get list of available dates for a given sport."""
        pass

    async def validate_connection(self) -> bool:
        """Test if the data source is accessible."""
        try:
            sports = await self.get_available_sports()
            return len(sports) > 0
        except Exception as e:
            self.logger.error(f"Connection validation failed: {e}")
            return False

    async def cleanup(self) -> None:
        """Clean up resources (close sessions, etc.)."""
        if self.session:
            await self.session.close()

    def __enter__(self) -> "BaseDataCollector":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Context manager exit."""
        asyncio.create_task(self.cleanup())


class BaseAPICollector(BaseDataCollector):
    """Base class for API-based data collectors."""

    def __init__(self, config: DataCollectionConfig):
        super().__init__(config)
        if config.source_type != DataSourceType.API:
            raise ValueError("Config source_type must be API for APICollector")

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the API."""
        if not self.session:
            import aiohttp

            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                headers=self.config.headers or {},
            )

        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        for attempt in range(self.config.max_retries):
            try:
                if self.session is None:
                    raise DataCollectionError("Session not initialized")
                async with self.session.get(
                    url, params=params, headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if isinstance(result, dict):
                            return result
                        else:
                            return {"data": result}
                    elif response.status == 429:  # Rate limited
                        wait_time = (attempt + 1) * self.config.rate_limit_delay
                        self.logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                    else:
                        response.raise_for_status()
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise DataCollectionError(
                        f"API request failed after {self.config.max_retries} "
                        f"attempts: {e}"
                    )
                await asyncio.sleep(self.config.rate_limit_delay)

        raise DataCollectionError("API request failed")


class BaseWebScrapingCollector(BaseDataCollector):
    """Base class for web scraping-based data collectors."""

    def __init__(self, config: DataCollectionConfig):
        super().__init__(config)
        if config.source_type != DataSourceType.WEB_SCRAPING:
            raise ValueError(
                "Config source_type must be WEB_SCRAPING for WebScrapingCollector"
            )

    async def _get_page_content(self, url: str) -> str:
        """Get HTML content from a webpage."""
        if not self.session:
            import aiohttp

            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                headers=self.config.headers or {},
            )

        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.text()

    async def _parse_html(self, html_content: str) -> Any:
        """Parse HTML content using BeautifulSoup."""
        from bs4 import BeautifulSoup

        return BeautifulSoup(html_content, "html.parser")


class DataCollectionManager:
    """
    Manages multiple data collectors and provides a unified interface.

    This class allows you to collect data from multiple sources and
    combine/compare the results.
    """

    def __init__(self) -> None:
        self.collectors: Dict[str, BaseDataCollector] = {}
        self.logger = logging.getLogger(f"{__name__}.DataCollectionManager")

    def add_collector(self, name: str, collector: BaseDataCollector) -> None:
        """Add a data collector to the manager."""
        self.collectors[name] = collector
        self.logger.info(f"Added collector: {name}")

    async def collect_from_all_sources(
        self, sport: SportType, game_date: Optional[date] = None
    ) -> Dict[str, List[PlayerProjection]]:
        """
        Collect projections from all available sources.

        Returns:
            Dictionary mapping source names to lists of projections
        """
        results = {}

        for name, collector in self.collectors.items():
            try:
                self.logger.info(f"Collecting from {name}")
                projections = await collector.collect_projections(sport, game_date)
                results[name] = projections
                self.logger.info(
                    f"Collected {len(projections)} projections from {name}"
                )
            except Exception as e:
                self.logger.error(f"Failed to collect from {name}: {e}")
                results[name] = []

        return results

    async def get_consensus_projections(
        self, sport: SportType, game_date: Optional[date] = None, min_sources: int = 2
    ) -> List[PlayerProjection]:
        """
        Get consensus projections from multiple sources.

        Args:
            sport: The sport to collect data for
            game_date: The date to collect data for
            min_sources: Minimum number of sources required for consensus

        Returns:
            List of consensus projections
        """
        all_projections = await self.collect_from_all_sources(sport, game_date)

        # Group projections by player
        player_projections: Dict[tuple, List[PlayerProjection]] = {}
        for source, projections in all_projections.items():
            for projection in projections:
                key = (projection.player_id, projection.player_name)
                if key not in player_projections:
                    player_projections[key] = []
                player_projections[key].append(projection)

        # Calculate consensus for players with enough sources
        consensus = []
        for (player_id, player_name), projections in player_projections.items():
            if len(projections) >= min_sources:
                # Calculate average projected points
                avg_points = sum(p.projected_points or 0 for p in projections) / len(
                    projections
                )
                avg_salary = sum(p.salary or 0 for p in projections) / len(projections)

                # Use the first projection as base and update with consensus values
                base_projection = projections[0]
                consensus_projection = PlayerProjection(
                    player_id=base_projection.player_id,
                    player_name=base_projection.player_name,
                    team=base_projection.team,
                    opponent=base_projection.opponent,
                    position=base_projection.position,
                    salary=int(avg_salary) if avg_salary > 0 else None,
                    projected_points=round(avg_points, 2),
                    projected_value=(
                        round(avg_points / avg_salary, 4) if avg_salary > 0 else None
                    ),
                    game_date=base_projection.game_date,
                    game_time=base_projection.game_time,
                    injury_status=base_projection.injury_status,
                    weather=base_projection.weather,
                    source="consensus",
                    last_updated=datetime.now(),
                    confidence=min(1.0, len(projections) / len(self.collectors)),
                )
                consensus.append(consensus_projection)

        return consensus

    async def cleanup(self) -> None:
        """Clean up all collectors."""
        for collector in self.collectors.values():
            await collector.cleanup()
