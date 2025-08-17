"""
Player name matching and standardization across different data sources.

This module provides utilities to standardize player names and match them
across different projection sources using Yahoo DFS as the reference.
"""

import re
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional


class PlayerNameMatcher:
    """Standardizes player names and matches across different data sources."""
    
    def __init__(self):
        self.yahoo_players_cache: Dict[str, Dict[str, Any]] = {}
    
    def standardize_name(self, name: str) -> str:
        """Standardize player name format for consistent matching."""
        if not name:
            return ""
        
        # Remove extra spaces, convert to lowercase for matching
        return re.sub(r'\s+', ' ', name.strip()).lower()
    
    def fuzzy_match(self, yahoo_name: str, projection_name: str, threshold: float = 0.8) -> bool:
        """
        Fuzzy match between Yahoo name and projection name.
        
        Args:
            yahoo_name: Player name from Yahoo DFS
            projection_name: Player name from projection source
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if names match above threshold
        """
        if not yahoo_name or not projection_name:
            return False
            
        yahoo_std = self.standardize_name(yahoo_name)
        proj_std = self.standardize_name(projection_name)
        
        # Exact match after standardization
        if yahoo_std == proj_std:
            return True
        
        # Handle common variations
        # 1. Initials vs full names (e.g., "A.J. Brown" vs "AJ Brown")
        yahoo_clean = re.sub(r'\.', '', yahoo_std)
        proj_clean = re.sub(r'\.', '', proj_std)
        if yahoo_clean == proj_clean:
            return True
        
        # 2. Handle Jr., Sr., III, etc.
        yahoo_no_suffix = re.sub(r'\s+(jr\.?|sr\.?|ii|iii|iv)$', '', yahoo_std)
        proj_no_suffix = re.sub(r'\s+(jr\.?|sr\.?|ii|iii|iv)$', '', proj_std)
        if yahoo_no_suffix == proj_no_suffix:
            return True
        
        # 3. Fuzzy matching for typos/variations
        similarity = SequenceMatcher(None, yahoo_std, proj_std).ratio()
        return similarity >= threshold
    
    def find_best_match(self, yahoo_name: str, candidate_names: List[str], threshold: float = 0.8) -> Optional[str]:
        """
        Find the best matching name from a list of candidates.
        
        Args:
            yahoo_name: Reference name from Yahoo
            candidate_names: List of names to match against
            threshold: Minimum similarity threshold
            
        Returns:
            Best matching name or None if no match above threshold
        """
        if not candidate_names:
            return None
            
        best_match = None
        best_score = 0.0
        
        for candidate in candidate_names:
            if self.fuzzy_match(yahoo_name, candidate, threshold):
                score = SequenceMatcher(None, 
                                      self.standardize_name(yahoo_name),
                                      self.standardize_name(candidate)).ratio()
                if score > best_score:
                    best_score = score
                    best_match = candidate
        
        return best_match
    
    def cache_yahoo_players(self, contest_id: str, players: List[Dict[str, Any]]) -> None:
        """Cache Yahoo players for a contest to avoid repeated API calls."""
        self.yahoo_players_cache[contest_id] = {
            player.get("name", ""): player for player in players if player.get("name")
        }
    
    def get_yahoo_player(self, contest_id: str, name: str) -> Optional[Dict[str, Any]]:
        """Get cached Yahoo player data by name."""
        return self.yahoo_players_cache.get(contest_id, {}).get(name)
    
    def clear_cache(self, contest_id: Optional[str] = None) -> None:
        """Clear player cache for a specific contest or all contests."""
        if contest_id:
            self.yahoo_players_cache.pop(contest_id, None)
        else:
            self.yahoo_players_cache.clear() 