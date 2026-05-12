#!/usr/bin/env bash
# Render build script for SHL Assessment Agent

set -o errexit  # Exit on error
set -o pipefail # Exit on pipe failure
set -o nounset  # Exit on undefined variable

echo "🔧 Starting build process..."

# Upgrade pip and build tools
echo "📦 Upgrading pip, setuptools, and wheel..."
pip install --upgrade --no-cache-dir pip setuptools wheel

# Install dependencies
echo "📚 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# Verify critical imports
echo "✅ Verifying installation..."
python -c "import fastapi; import uvicorn; import groq; import httpx; print('All imports successful!')"

echo "✨ Build complete!"
