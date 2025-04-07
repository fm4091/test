#!/bin/bash

# Setup script for Document De-Identifier project

echo "Setting up Document De-Identifier..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Download spaCy model
echo "Downloading spaCy model..."
python3 -m spacy download en_core_web_lg

# Create necessary directories
echo "Creating project directories..."
mkdir -p data/input data/output

# Make scripts executable
echo "Making scripts executable..."
chmod +x run_demo.sh
chmod +x src/*.py

echo "Setup complete! To activate the environment, run:"
echo "source venv/bin/activate"
echo ""
echo "To run the demo, use:"
echo "./run_demo.sh" 