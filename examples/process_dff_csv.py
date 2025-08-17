#!/usr/bin/env python3
"""
Example script demonstrating how to use the Daily Fantasy Fuel collector.

This script shows how to:
1. Automatically scrape Daily Fantasy Fuel website
2. Download CSV projections automatically
3. Convert them to our PlayerProjection format
4. Integrate with the data collection manager
5. Compare projections from multiple sources
"""

import asyncio
import logging
from datetime import date
from pathlib import Path
import sys

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_collection.base import DataCollectionManager, SportType
from data_collection.collectors import (
    BasketballReferenceCollector,
    DailyFantasyFuelCollector,
)


async def main():
    """Main function demonstrating Daily Fantasy Fuel data collection."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Create data collection manager
    manager = DataCollectionManager()

    try:
        # Add collectors
        br_collector = BasketballReferenceCollector()
        dff_collector = DailyFantasyFuelCollector()

        manager.add_collector("Basketball Reference", br_collector)
        manager.add_collector("Daily Fantasy Fuel", dff_collector)

        logger.info("Starting data collection...")

        # Example 1: Test connection to Daily Fantasy Fuel
        logger.info("Example 1: Testing Daily Fantasy Fuel connection")
        try:
            if await dff_collector.validate_connection():
                logger.info("✓ Daily Fantasy Fuel connection successful")
            else:
                logger.error("✗ Daily Fantasy Fuel connection failed")
        except Exception as e:
            logger.warning(f"Connection test failed (may require authentication): {e}")

        # Example 2: Get available sports and dates
        logger.info("\nExample 2: Available sports and dates")
        sports = await dff_collector.get_available_sports()
        logger.info(f"Daily Fantasy Fuel supports: {[s.value for s in sports]}")

        # Get available dates for NBA
        try:
            dates = await dff_collector.get_available_dates(SportType.NBA)
            logger.info(f"Available dates for NBA: {dates}")
        except Exception as e:
            logger.warning(f"Could not get available dates: {e}")

        # Example 3: Collect NBA projections from Daily Fantasy Fuel
        logger.info("\nExample 3: Collecting NBA projections from Daily Fantasy Fuel")
        try:
            dff_projections = await dff_collector.collect_projections(SportType.NBA)
            logger.info(
                f"Successfully collected {len(dff_projections)} projections from Daily Fantasy Fuel"
            )

            # Display some projections
            if dff_projections:
                logger.info("Sample projections:")
                for i, proj in enumerate(dff_projections[:5], 1):
                    logger.info(
                        f"  {i}. {proj.player_name} ({proj.team}) - {proj.position} - "
                        f"${proj.salary:,} - {proj.projected_points} pts"
                    )
            else:
                logger.info("No projections collected (may require authentication)")

        except Exception as e:
            logger.warning(f"Could not collect from Daily Fantasy Fuel: {e}")
            logger.info("This is expected if authentication is required")

        # Example 4: Collect from Basketball Reference as fallback
        logger.info("\nExample 4: Collecting from Basketball Reference (free source)")
        try:
            br_projections = await br_collector.collect_projections(SportType.NBA)
            logger.info(
                f"Collected {len(br_projections)} projections from Basketball Reference"
            )
        except Exception as e:
            logger.error(f"Failed to collect from Basketball Reference: {e}")
            br_projections = []

        # Example 5: Show how to handle authentication
        logger.info("\nExample 5: Authentication handling")
        logger.info("Daily Fantasy Fuel may require authentication for CSV downloads.")
        logger.info("To use with authentication:")
        logger.info(
            """
        # Check if login is required
        if await dff_collector.login_if_required(username, password):
            # Now try to collect projections
            projections = await dff_collector.collect_projections(SportType.NBA)
        """
        )

        # Example 6: Show supported platforms
        logger.info("\nExample 6: Supported platforms and features")
        logger.info(
            f"Daily Fantasy Fuel supports: {dff_collector.get_supported_platforms()}"
        )
        logger.info(f"Sport URL patterns: {dff_collector.sport_urls}")

        # Example 7: Manual CSV processing (fallback method)
        logger.info("\nExample 7: Manual CSV processing (fallback)")
        logger.info(
            "If automatic scraping fails, you can still process CSV exports manually:"
        )
        logger.info(
            """
        # This would be used if you manually download CSV from the website
        from data_collection.collectors.daily_fantasy_fuel import DailyFantasyFuelCollector
        
        # Create a simple CSV processor
        class CSVProcessor:
            def process_csv(self, csv_content, sport):
                # Parse CSV and convert to PlayerProjection objects
                # Implementation would be similar to the original collector
                pass
        """
        )

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
