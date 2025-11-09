#!/bin/bash

# Post-create script for dev container setup

echo "🚀 Setting up development environment..."

# Install backend dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install frontend dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend && npm install && cd ..

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p artifacts temp logs

# Set permissions
chmod 755 artifacts temp logs

# Git configuration
echo "🔧 Configuring git..."
git config --global --add safe.directory /workspace

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Update .env file with your configuration"
echo "  2. Run 'cd backend && python -m uvicorn main:app --reload' to start backend"
echo "  3. Run 'cd frontend && npm run dev' to start frontend"
echo ""
