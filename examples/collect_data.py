#!/usr/bin/env python3
"""
Example script demonstrating how to use the DFS data collection system.

This script shows how to:
1. Set up data collectors
2. Collect projections from multiple sources
3. Get consensus projections
4. Handle errors gracefully
"""

import asyncio
import logging
from datetime import date
from pathlib import Path
import sys

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_collection.base import DataCollectionManager, SportType
from data_collection.collectors import BasketballReferenceCollector


async def main():
    """Main function demonstrating data collection."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Create data collection manager
    manager = DataCollectionManager()
    
    try:
        # Add Basketball Reference collector
        br_collector = BasketballReferenceCollector()
        manager.add_collector("Basketball Reference", br_collector)
        
        logger.info("Starting data collection...")
        
        # Test connection to Basketball Reference
        logger.info("Testing connection to Basketball Reference...")
        if await br_collector.validate_connection():
            logger.info("✓ Basketball Reference connection successful")
        else:
            logger.error("✗ Basketball Reference connection failed")
            return
        
        # Get available sports
        sports = await br_collector.get_available_sports()
        logger.info(f"Available sports: {[sport.value for sport in sports]}")
        
        # Collect NBA projections for today
        logger.info("Collecting NBA projections...")
        projections = await manager.collect_from_all_sources(SportType.NBA)
        
        # Display results
        for source_name, source_projections in projections.items():
            logger.info(f"\n{source_name}: {len(source_projections)} projections")
            
            if source_projections:
                # Show top 5 projections by points
                sorted_projections = sorted(
                    source_projections, 
                    key=lambda p: p.projected_points or 0, 
                    reverse=True
                )
                
                logger.info("Top 5 projections:")
                for i, proj in enumerate(sorted_projections[:5], 1):
                    logger.info(
                        f"  {i}. {proj.player_name} ({proj.team}) - "
                        f"{proj.position} - {proj.projected_points} pts"
                    )
        
        # Get consensus projections (if we have multiple sources)
        if len(manager.collectors) > 1:
            logger.info("\nGetting consensus projections...")
            consensus = await manager.get_consensus_projections(
                SportType.NBA, 
                min_sources=2
            )
            logger.info(f"Consensus projections: {len(consensus)} players")
        
        # Show some statistics
        total_projections = sum(len(projs) for projs in projections.values())
        logger.info(f"\nTotal projections collected: {total_projections}")
        
        if total_projections > 0:
            # Calculate average projected points
            all_projections = []
            for projs in projections.values():
                all_projections.extend(projs)
            
            avg_points = sum(p.projected_points or 0 for p in all_projections) / len(all_projections)
            logger.info(f"Average projected points: {avg_points:.2f}")
            
            # Show position breakdown
            positions = {}
            for proj in all_projections:
                pos = proj.position
                if pos not in positions:
                    positions[pos] = 0
                positions[pos] += 1
            
            logger.info("Position breakdown:")
            for pos, count in sorted(positions.items()):
                logger.info(f"  {pos}: {count} players")
    
    except Exception as e:
        logger.error(f"Error during data collection: {e}")
        raise
    
    finally:
        # Clean up
        await manager.cleanup()
        logger.info("Data collection completed.")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 