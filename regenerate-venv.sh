#!/bin/bash
set -e

echo "🔧 VideoAI Environment Setup Script"
echo "=================================="

# Remove existing virtual environment
if [ -d "venv" ]; then
    echo "📦 Removing existing virtual environment..."
    rm -rf venv
fi

# Create new virtual environment
echo "🐍 Creating new Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install production dependencies
echo "📦 Installing production dependencies..."
pip install -r requirements.txt

# Install development dependencies
echo "🛠️  Installing development dependencies..."
pip install black ruff mypy pytest pytest-asyncio pytest-cov pre-commit

# Install the project in development mode
echo "📦 Installing VideoAI in development mode..."
pip install -e .

# Setup pre-commit hooks
echo "🔗 Setting up pre-commit hooks..."
pre-commit install || echo "⚠️  pre-commit not available, skipping hooks setup"

echo ""
echo "✅ Environment setup complete!"
echo ""
echo "To activate the environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run development tools:"
echo "  black .          # Format code"
echo "  ruff .           # Lint code" 
echo "  mypy app/       # Type check"
echo "  pytest          # Run tests"
echo ""
echo "To run the application:"
echo "  uvicorn app.main:app --reload"
