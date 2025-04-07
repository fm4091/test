#!/bin/bash

# Demo script for PDF De-identification

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Create directories if they don't exist
mkdir -p data/input data/output

echo "=== Step 1: Generating sample PDF with PII data ==="
python3 src/generate_sample_pdf.py --num-records 5
echo ""

# Check if sample PDF was created
if [ ! -f "data/input/sample_with_pii.pdf" ]; then
    echo "Error: Failed to generate sample PDF."
    exit 1
fi

echo "=== Step 2: De-identifying the PDF ==="
python3 src/pdf_deidentify.py --input data/input/sample_with_pii.pdf --output data/output --format json
echo ""

# Check if output was created
if [ ! -f "data/output/sample_with_pii_processed.json" ]; then
    echo "Error: Failed to create de-identified output."
    exit 1
fi

echo "=== Step 3: Converting JSON back to readable format ==="
python3 src/pdf_deidentify.py --input data/input/sample_with_pii.pdf --output data/output --format txt
echo ""

echo "=== Step 4: Creating visualization of de-identified fields ==="
python3 src/visualize_deidentification.py --input data/input/sample_with_pii.pdf --mappings data/output/sample_with_pii_mappings.json --output data/output/sample_with_pii_visualized.pdf
echo ""

# Check if visualization was created
if [ ! -f "data/output/sample_with_pii_visualized.pdf" ]; then
    echo "Warning: Visualization could not be created. This may be due to missing pymupdf dependency."
    echo "To install it, run: pip3 install pymupdf"
else
    echo "Visualization created successfully!"
    
    # Try to open the PDF on different platforms
    if [ "$(uname)" == "Darwin" ]; then  # macOS
        open data/output/sample_with_pii_visualized.pdf &
    elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        if command -v xdg-open > /dev/null; then
            xdg-open data/output/sample_with_pii_visualized.pdf &
        else
            echo "PDF viewer not found. Please open the PDF manually."
        fi
    elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW32_NT" ]; then  # Windows
        start data/output/sample_with_pii_visualized.pdf &
    else
        echo "Please open the PDF manually to view the visualization."
    fi
fi

echo "=== Demo Complete! ==="
echo "Original PDF: data/input/sample_with_pii.pdf"
echo "De-identified JSON: data/output/sample_with_pii_processed.json"
echo "De-identified text: data/output/sample_with_pii_processed.txt"
echo "PII mappings: data/output/sample_with_pii_mappings.json"
echo "Visualization: data/output/sample_with_pii_visualized.pdf"
echo ""
echo "To re-identify the data, you can run:"
echo "python3 src/pdf_deidentify.py --input data/input/sample_with_pii.pdf --output data/output --mode deanonymize --mappings data/output/sample_with_pii_mappings.json" 