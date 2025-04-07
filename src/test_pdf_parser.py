#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for PDF parser functionality.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Import the PDF parser
from parsers.pdf_parser import PDFParser
from utils import ensure_dir

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Test the PDF parser by parsing a sample PDF."""
    # Check if a sample PDF is provided as argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Look for PDFs in the data/input directory
        input_dir = Path('data/input')
        pdf_files = list(input_dir.glob('*.pdf'))
        
        if not pdf_files:
            logger.error("No PDF files found in data/input directory.")
            logger.info("Please run 'python src/generate_sample_pdf.py' first or provide a PDF path as argument.")
            sys.exit(1)
        
        pdf_path = str(pdf_files[0])
    
    logger.info(f"Testing PDF parser with file: {pdf_path}")
    
    # Initialize the PDF parser
    parser = PDFParser()
    
    try:
        # Parse the PDF
        result = parser.parse(pdf_path)
        
        # Print some information about the parsed PDF
        logger.info(f"Successfully parsed PDF with {len(result['pages'])} pages.")
        
        # Check if there are tables
        total_tables = sum(len(page['tables']) for page in result['pages'])
        logger.info(f"Found {total_tables} tables in the PDF.")
        
        # Save the parsed results to a JSON file
        output_dir = ensure_dir(Path('data/output'))
        output_file = output_dir / f"{Path(pdf_path).stem}_parsed.json"
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Saved parsed PDF data to {output_file}")
        
        # Save as text for easy reading
        text_file = output_dir / f"{Path(pdf_path).stem}_parsed.txt"
        
        with open(text_file, 'w') as f:
            f.write(f"PDF METADATA:\n")
            for key, value in result['metadata'].items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")
            
            for page in result['pages']:
                f.write(f"PAGE {page['page_num']}:\n")
                f.write("-" * 80 + "\n")
                f.write(page['text'])
                f.write("\n\n")
                
                for i, table in enumerate(page['tables']):
                    f.write(f"TABLE {i+1}:\n")
                    f.write("-" * 80 + "\n")
                    f.write(table['raw_data'])
                    f.write("\n\n")
        
        logger.info(f"Saved parsed PDF text to {text_file}")
        
    except Exception as e:
        logger.error(f"Error parsing PDF: {str(e)}")
        logger.debug("Exception details:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 