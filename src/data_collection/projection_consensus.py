"""
Projection consensus and source weighting across different data sources.

This module provides utilities to determine which projection source to use
for each player and aggregate projections from multiple sources.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ProjectionSource(Enum):
    """Enumeration of available projection sources."""
    DAILY_FANTASY_FUEL = "dailyfantasyfuel"
    ROTOWIRE = "rotowire"
    YAHOO = "yahoo"
    FANTASYPROS = "fantasypros"
    NUMBERFIRE = "numberfire"


@dataclass
class PlayerProjection:
    """Data structure for player projections from different sources."""
    player_name: str
    source: ProjectionSource
    projection_value: float
    confidence: Optional[float] = None
    last_updated: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProjectionConsensus:
    """Determines which projection source to use for each player."""
    
    def __init__(self, source_weights: Optional[Dict[str, float]] = None):
        """
        Initialize with custom source weights.
        
        Args:
            source_weights: Dict mapping source names to weights (0.0 to 1.0)
        """
        # Default weights - can be customized
        self.source_weights = source_weights or {
            ProjectionSource.DAILY_FANTASY_FUEL.value: 0.35,
            ProjectionSource.ROTOWIRE.value: 0.30,
            ProjectionSource.YAHOO.value: 0.20,
            ProjectionSource.FANTASYPROS.value: 0.10,
            ProjectionSource.NUMBERFIRE.value: 0.05,
        }
        
        # Normalize weights to sum to 1.0
        total_weight = sum(self.source_weights.values())
        if total_weight > 0:
            self.source_weights = {k: v/total_weight for k, v in self.source_weights.items()}
    
    def get_best_projection(self, player_projections: Dict[str, float]) -> Tuple[Optional[str], float]:
        """
        Return the best projection source and value for a player.
        
        Args:
            player_projections: Dict mapping source names to projection values
            
        Returns:
            Tuple of (best_source, consensus_projection)
        """
        if not player_projections:
            return None, 0.0
        
        # Calculate weighted average
        weighted_sum = 0.0
        total_weight = 0.0
        available_sources = []
        
        for source, projection in player_projections.items():
            if source in self.source_weights and projection is not None:
                weight = self.source_weights[source]
                weighted_sum += projection * weight
                total_weight += weight
                available_sources.append(source)
        
        if total_weight == 0:
            return None, 0.0
        
        consensus_projection = weighted_sum / total_weight
        
        # Return source with highest weight that has data
        best_source = max(available_sources, key=lambda s: self.source_weights.get(s, 0))
        
        return best_source, consensus_projection
    
    def get_consensus_projection(self, player_projections: Dict[str, float]) -> float:
        """
        Get consensus projection value (weighted average).
        
        Args:
            player_projections: Dict mapping source names to projection values
            
        Returns:
            Weighted average projection value
        """
        _, consensus_value = self.get_best_projection(player_projections)
        return consensus_value
    
    def rank_sources_by_quality(self, player_projections: Dict[str, float]) -> List[Tuple[str, float]]:
        """
        Rank projection sources by quality (weight) for a player.
        
        Args:
            player_projections: Dict mapping source names to projection values
            
        Returns:
            List of (source, weight) tuples sorted by weight
        """
        available_sources = [
            (source, self.source_weights.get(source, 0))
            for source in player_projections.keys()
            if source in self.source_weights and player_projections[source] is not None
        ]
        
        return sorted(available_sources, key=lambda x: x[1], reverse=True)
    
    def update_source_weight(self, source: str, new_weight: float) -> None:
        """
        Update the weight for a specific projection source.
        
        Args:
            source: Source name to update
            new_weight: New weight value (0.0 to 1.0)
        """
        if source in self.source_weights:
            self.source_weights[source] = max(0.0, min(1.0, new_weight))
            # Re-normalize weights
            total_weight = sum(self.source_weights.values())
            if total_weight > 0:
                self.source_weights = {k: v/total_weight for k, v in self.source_weights.items()}
    
    def get_source_weights(self) -> Dict[str, float]:
        """Get current source weights."""
        return self.source_weights.copy()
    
    def reset_to_default_weights(self) -> None:
        """Reset source weights to default values."""
        self.__init__()


class ProjectionAggregator:
    """Aggregates projections from multiple sources for multiple players."""
    
    def __init__(self, consensus: ProjectionConsensus):
        """
        Initialize with a projection consensus engine.
        
        Args:
            consensus: ProjectionConsensus instance
        """
        self.consensus = consensus
    
    def aggregate_player_projections(self, all_projections: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate projections for multiple players.
        
        Args:
            all_projections: Dict mapping player names to their projections by source
            
        Returns:
            Dict mapping player names to aggregated projection data
        """
        aggregated = {}
        
        for player_name, projections in all_projections.items():
            best_source, consensus_value = self.consensus.get_best_projection(projections)
            source_rankings = self.consensus.rank_sources_by_quality(projections)
            
            aggregated[player_name] = {
                "consensus_projection": consensus_value,
                "best_source": best_source,
                "source_rankings": source_rankings,
                "all_projections": projections,
                "projection_count": len([p for p in projections.values() if p is not None])
            }
        
        return aggregated 