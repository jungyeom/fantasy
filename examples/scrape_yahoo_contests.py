#!/usr/bin/env python3
"""
Example script demonstrating how to use the Yahoo DFS collector.

This script shows how to:
1. Scrape contest information from Yahoo DFS
2. Filter for multi-entry contests only
3. Extract key contest details (fees, prize pools, entry limits)
4. Analyze contest statistics
5. Filter by contest types
"""

import asyncio
import logging
from datetime import date
from pathlib import Path
import sys

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_collection.base import SportType
from data_collection.collectors import YahooDFSCollector


async def main():
    """Main function demonstrating Yahoo DFS contest collection."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Create Yahoo DFS collector
    yahoo_collector = YahooDFSCollector()

    try:
        logger.info("Starting Yahoo DFS contest collection...")

        # Example 1: Test connection to Yahoo DFS
        logger.info("Example 1: Testing Yahoo DFS connection")
        try:
            if await yahoo_collector.validate_connection():
                logger.info("✓ Yahoo DFS connection successful")
            else:
                logger.error("✗ Yahoo DFS connection failed")
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")

        # Example 2: Get available sports and dates
        logger.info("\nExample 2: Available sports and dates")
        sports = yahoo_collector.get_available_sports()
        logger.info(f"Yahoo DFS supports: {[s.value for s in sports]}")

        # Get available dates for NFL
        try:
            dates = yahoo_collector.get_available_dates(SportType.NFL)
            logger.info(f"Available dates for NFL: {dates}")
        except Exception as e:
            logger.warning(f"Could not get available dates: {e}")

        # Example 3: Collect NFL contests (multi-entry only)
        logger.info("\nExample 3: Collecting NFL contests (multi-entry only)")
        try:
            nfl_contests = await yahoo_collector.collect_contests(SportType.NFL)
            logger.info(
                f"Successfully collected {len(nfl_contests)} multi-entry NFL contests"
            )

            # Display contest details
            if nfl_contests:
                logger.info("Sample contests:")
                for i, contest in enumerate(nfl_contests[:5], 1):
                    logger.info(
                        f"  {i}. {contest.contest_name} - "
                        f"${contest.entry_fee} entry - "
                        f"${contest.total_prize_pool:,} prize pool - "
                        f"{contest.max_entries_per_user} max entries per user"
                    )
            else:
                logger.info("No multi-entry contests found")

        except Exception as e:
            logger.warning(f"Could not collect from Yahoo DFS: {e}")
            logger.info("This may be expected if the site structure has changed")

        # Example 4: Collect NBA contests with specific filters
        logger.info("\nExample 4: Collecting NBA contests with filters")
        try:
            nba_contests = await yahoo_collector.collect_contests(
                SportType.NBA, contest_types=["Guaranteed", "Multi Entry"]
            )
            logger.info(f"Found {len(nba_contests)} filtered NBA contests")

        except Exception as e:
            logger.warning(f"Could not collect NBA contests: {e}")
            nba_contests = []

        # Example 5: Analyze contest statistics
        logger.info("\nExample 5: Contest statistics analysis")
        all_contests = nfl_contests + nba_contests

        if all_contests:
            stats = yahoo_collector.get_contest_statistics(all_contests)

            logger.info("Contest Statistics:")
            logger.info(f"  Total contests: {stats['total_contests']}")
            logger.info(f"  Total prize pools: ${stats['total_prize_pools']:,.2f}")
            logger.info(f"  Average entry fee: ${stats['average_entry_fee']:.2f}")

            logger.info("  Contest types:")
            for contest_type, count in stats["contest_type_distribution"].items():
                logger.info(f"    {contest_type}: {count}")

            logger.info("  Multi-entry vs Single-entry:")
            logger.info(f"    Multi-entry: {stats['multi_entry_count']}")
            logger.info(f"    Single-entry: {stats['single_entry_count']}")
            logger.info(f"    Multi-entry percentage: {stats['multi_entry_percentage']:.1f}%")

        # Example 6: Filter contests by specific criteria
        logger.info("\nExample 6: Filtering contests by criteria")
        if all_contests:
            # High-stakes contests (entry fee > $50)
            high_stakes = [c for c in all_contests if c.entry_fee > 50]
            logger.info(f"High-stakes contests (>$50): {len(high_stakes)}")

            # Large prize pools (>$100,000)
            large_pools = [c for c in all_contests if c.total_prize_pool > 100000]
            logger.info(f"Large prize pool contests (>$100K): {len(large_pools)}")

            # Guaranteed contests only
            guaranteed = [c for c in all_contests if c.guaranteed]
            logger.info(f"Guaranteed contests: {len(guaranteed)}")

            # Multi-entry contests with high limits
            high_limits = [c for c in all_contests if c.max_entries_per_user > 10]
            logger.info(f"High entry limit contests (>10): {len(high_limits)}")

        # Example 7: Show how to use contest data for lineup optimization
        logger.info("\nExample 7: Using contest data for lineup optimization")
        logger.info("Contest information can be used to:")
        logger.info("  - Calculate optimal number of lineups to enter")
        logger.info("  - Determine bankroll allocation")
        logger.info("  - Choose contests with best value")
        logger.info("  - Implement contest-specific strategies")

        if all_contests:
            # Example: Find best value contests (lowest entry fee relative to prize pool)
            value_contests = sorted(
                all_contests,
                key=lambda c: (
                    c.entry_fee / c.total_prize_pool
                    if c.total_prize_pool > 0
                    else float("inf")
                ),
            )

            if value_contests:
                best_value = value_contests[0]
                logger.info(f"Best value contest: {best_value.contest_name}")
                logger.info(f"  Entry fee: ${best_value.entry_fee}")
                logger.info(f"  Prize pool: ${best_value.total_prize_pool:,}")
                logger.info(
                    f"  Value ratio: {best_value.entry_fee / best_value.total_prize_pool:.6f}"
                )

    except Exception as e:
        logger.error(f"Error during contest collection: {e}")
        raise

    finally:
        # Clean up
        await yahoo_collector.cleanup()
        logger.info("Contest collection completed.")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
