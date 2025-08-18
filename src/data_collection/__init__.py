"""
Data collection package for fantasy sports optimization.

This package provides abstract interfaces and concrete implementations
for collecting player projections and contest information from various
fantasy sports data sources.
"""

from .base import (
    BaseDataCollector,
    BaseAPICollector,
    BaseWebScrapingCollector,
    DataCollectionManager,
    PlayerProjection,
    SportType,
    DataSourceType,
    DataCollectionConfig,
    DataCollectionError,
)

from .collectors import (
    BasketballReferenceCollector,
    DailyFantasyFuelCollector,
    YahooDFSCollector,
)

from .player_matching import PlayerNameMatcher
from .projection_consensus import (
    ProjectionConsensus,
    ProjectionAggregator,
    ProjectionSource,
    PlayerProjection as ConsensusPlayerProjection,
)
from .lineup_optimizer import main as run_lineup_optimizer
from .pipeline import DFSPipeline, main as run_pipeline

__all__ = [
    # Base classes
    "BaseDataCollector",
    "BaseAPICollector",
    "BaseWebScrapingCollector",
    "DataCollectionManager",
    "PlayerProjection",
    "SportType",
    "DataSourceType",
    "DataCollectionConfig",
    "DataCollectionError",

    # Collectors
    "BasketballReferenceCollector",
    "DailyFantasyFuelCollector",
    "YahooDFSCollector",

    # Player matching and consensus
    "PlayerNameMatcher",
    "ProjectionConsensus",
    "ProjectionAggregator",
    "ProjectionSource",
    "ConsensusPlayerProjection",

    # Lineup optimization
    "run_lineup_optimizer",
    
    # Pipeline
    "DFSPipeline",
    "run_pipeline",
]
