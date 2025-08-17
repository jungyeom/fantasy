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

### Running the Example

```bash
# Using uv (recommended)
uv run python examples/collect_data.py

# Or activate virtual environment first
source .venv/bin/activate
python examples/collect_data.py
```

### Adding New Data Sources

1. Create a new collector class extending `BaseDataCollector`
2. Implement the required abstract methods
3. Add configuration to `config/data_sources.yaml`
4. Register with the `DataCollectionManager`

## Project Structure

```
fantasy/
├── src/
│   └── data_collection/
│       ├── __init__.py
│       ├── base.py              # Abstract base classes
│       └── collectors/          # Concrete implementations
│           ├── __init__.py
│           └── basketball_reference.py
├── config/
│   └── data_sources.yaml       # Data source configuration
├── examples/
│   └── collect_data.py         # Example usage script
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