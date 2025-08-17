#!/bin/bash
# Development setup script for DFS Fantasy project

echo "🚀 Setting up DFS Fantasy development environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv is installed: $(uv --version)"

# Create virtual environment and install dependencies
echo "📦 Installing dependencies..."
uv sync --extra dev

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
uv run pre-commit install

# Run tests to verify setup
echo "🧪 Running tests to verify setup..."
uv run pytest --version

echo "✅ Development environment setup complete!"
echo ""
echo "Common uv commands:"
echo "  uv sync                    # Install all dependencies"
echo "  uv sync --extra dev       # Install dev dependencies"
echo "  uv run python script.py   # Run Python script in virtual env"
echo "  uv run pytest             # Run tests"
echo "  uv run black .            # Format code"
echo "  uv run flake8 .           # Lint code"
echo "  uv run mypy src/          # Type check"
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate" 