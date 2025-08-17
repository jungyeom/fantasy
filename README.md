# DFS Fantasy Sports Project

Welcome to the DFS Fantasy Sports project! This is a comprehensive system for optimizing daily fantasy sports lineups using Yahoo DFS and multiple data sources for player projections.

## Getting Started

This project is designed to help DFS players optimize their lineups by collecting player projections from multiple sources and using advanced algorithms to create optimal lineups.

### Prerequisites

- Python 3.8+
- pip or conda for package management
- Yahoo DFS account (for lineup submission)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/fantasy.git
   cd fantasy
   ```

2. Install dependencies:
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or install development dependencies
   uv sync --extra dev
   
   # Alternative: using pip
   pip install -r requirements.txt
   ```

3. Set up configuration:
   - Copy `config/data_sources.yaml.example` to `config/data_sources.yaml`
   - Update with your API keys and preferences

## Features

- **Multi-Source Data Collection**: Abstract layer for collecting player projections from various free and paid sources
- **Yahoo DFS Integration**: Direct integration with Yahoo Daily Fantasy Sports
- **Lineup Optimization**: Advanced algorithms for creating optimal DFS lineups
- **Data Aggregation**: Consensus projections from multiple sources for improved accuracy
- **Extensible Architecture**: Easy to add new data sources and sports
- **Rate Limiting & Caching**: Respectful data collection with intelligent caching

## Installation

See the Getting Started section above for detailed installation instructions.

## Usage

### Basic Data Collection

```python
from src.data_collection.base import DataCollectionManager, SportType
from src.data_collection.collectors import BasketballReferenceCollector

# Create manager and add collectors
manager = DataCollectionManager()
manager.add_collector("Basketball Reference", BasketballReferenceCollector())

# Collect NBA projections
projections = await manager.collect_from_all_sources(SportType.NBA)

# Get consensus projections
consensus = await manager.get_consensus_projections(SportType.NBA, min_sources=2)
```

### Running the Examples

```bash
# Basic data collection example
uv run python examples/collect_data.py

# Daily Fantasy Fuel CSV processing example
uv run python examples/process_dff_csv.py

# Yahoo DFS contest scraping example
uv run python examples/scrape_yahoo_contests.py

# Or use the Makefile
make run-example
make run-dff-example
make run-yahoo-example
```

### Adding New Data Sources

1. Create a new collector class extending `BaseDataCollector`
2. Implement the required abstract methods
3. Add configuration to `config/data_sources.yaml`
4. Register with the `DataCollectionManager`

### Yahoo DFS Contest Information

The project now includes a dedicated collector for [Yahoo DFS](https://sports.yahoo.com/dailyfantasy) contest information that covers:

- **Sports**: NFL, NBA, MLB, NHL
- **Data Type**: Contest information and structure
- **Features**: Entry fees, prize pools, entry limits, contest types
- **Focus**: Multi-entry contests only

#### Usage:

```python
from data_collection.collectors import YahooDFSCollector
from data_collection.base import SportType

# Create collector
yahoo_collector = YahooDFSCollector()

# Collect multi-entry contests for NFL
contests = await yahoo_collector.collect_contests(SportType.NFL)

# Filter by contest types
guaranteed_contests = await yahoo_collector.collect_contests(
    SportType.NBA,
    contest_types=["Guaranteed", "Multi Entry"]
)

# Get contest statistics
stats = yahoo_collector.get_contest_statistics(contests)
```

#### Contest Information Collected:

- **Entry Fee**: Cost to enter each contest
- **Prize Pool**: Total prize money available
- **Entry Limits**: Maximum entries per user and total contest entries
- **Contest Types**: Guaranteed, Qualifier, Satellite, etc.
- **Entry Limit Types**: Single Entry, Multi Entry, Max Entries

#### How It Works:

1. **Automatic Navigation**: Navigates to sport-specific DFS pages
2. **Contest Detection**: Finds contest containers using multiple methods
3. **Data Extraction**: Parses contest details from HTML content
4. **Multi-Entry Filtering**: Automatically filters for contests allowing multiple entries
5. **Statistical Analysis**: Provides contest statistics and analysis tools

### Daily Fantasy Fuel Integration

The project now includes a dedicated collector for [Daily Fantasy Fuel](https://www.dailyfantasyfuel.com/), a premium DFS projections service that covers:

- **Sports**: NFL, NBA, MLB, NHL, WNBA
- **Platforms**: DraftKings, FanDuel
- **Data Format**: Automatic CSV downloads via web scraping
- **Features**: Player projections, salaries, injury status, starting lineups

#### Usage:

```python
from data_collection.collectors import DailyFantasyFuelCollector
from data_collection.base import SportType

# Create collector
dff_collector = DailyFantasyFuelCollector()

# Automatically scrape and download projections
projections = await dff_collector.collect_projections(SportType.NBA)

# Check if authentication is required
if await dff_collector.login_if_required(username, password):
    projections = await dff_collector.collect_projections(SportType.NFL)
```

#### How It Works:

1. **Automatic Navigation**: The collector navigates to sport-specific pages on Daily Fantasy Fuel
2. **CSV Link Detection**: Searches for CSV download links using multiple methods
3. **Automatic Download**: Downloads CSV files directly from the website
4. **Data Parsing**: Converts CSV data to our standardized `PlayerProjection` format
5. **Authentication Support**: Handles login requirements for premium content

#### CSV Format Requirements:

The collector automatically handles CSV files with these columns:
- `Player`: Player name
- `Team`: Player's team
- `Opponent`: Opposing team
- `Position`: Player position
- `Salary`: Player salary
- `Projected_Points`: Expected fantasy points
- `Game_Date`: Game date
- `Injury_Status`: Injury information (optional)

## Project Structure

```
fantasy/
├── src/
│   └── data_collection/
│       ├── __init__.py
│       ├── base.py              # Abstract base classes
│       └── collectors/          # Concrete implementations
│           ├── __init__.py
│           ├── basketball_reference.py
│           ├── daily_fantasy_fuel.py
│           └── yahoo_dfs.py
├── config/
│   └── data_sources.yaml       # Data source configuration
├── examples/
│   ├── collect_data.py         # Basic data collection example
│   ├── process_dff_csv.py      # Daily Fantasy Fuel CSV processing
│   └── scrape_yahoo_contests.py # Yahoo DFS contest scraping
├── scripts/
│   └── dev-setup.sh            # Development setup script
├── pyproject.toml              # Project configuration and dependencies
├── Makefile                    # Common development tasks
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

[Your contact information can be added here] 