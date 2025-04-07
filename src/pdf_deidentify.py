#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF De-identifier: A specialized script for de-identifying PDF documents.
This script focuses solely on PDF processing and provides a simpler interface 
than the main application.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Import internal modules
from parsers.pdf_parser import PDFParser
from deidentifier import Deidentifier
from utils import ensure_dir, save_json, load_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='De-identify PII in PDF documents.'
    )
    
    parser.add_argument(
        '--input', '-i', 
        type=str, 
        required=True,
        help='Path to input PDF file'
    )
    
    parser.add_argument(
        '--output', '-o', 
        type=str, 
        default='data/output',
        help='Path to output directory (default: data/output)'
    )
    
    parser.add_argument(
        '--mode', '-m',
        type=str,
        choices=['anonymize', 'deanonymize'],
        default='anonymize',
        help='Mode: anonymize (de-identify) or deanonymize (re-identify)'
    )
    
    parser.add_argument(
        '--mappings', 
        type=str,
        help='Path to mappings JSON file (required for deanonymize mode)'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        choices=['txt', 'json', 'pdf'],
        default='json',
        help='Output format (default: json)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()

def process_pdf(input_path, output_dir, output_format='json', mode='anonymize', mappings_path=None):
    """
    Process a PDF file by de-identifying or re-identifying PII.
    
    Args:
        input_path: Path to the input PDF file
        output_dir: Directory to save output files
        output_format: Format for the output file (txt, json, pdf)
        mode: 'anonymize' or 'deanonymize'
        mappings_path: Path to mappings file (required for deanonymize mode)
        
    Returns:
        Tuple of (output_file_path, mappings_file_path)
    """
    # Ensure output directory exists
    output_dir = ensure_dir(output_dir)
    
    # Initialize the parser
    pdf_parser = PDFParser()
    
    # Initialize the de-identifier
    deidentifier = Deidentifier()
    
    # Parse the PDF
    logger.info(f"Parsing PDF: {input_path}")
    pdf_content = pdf_parser.parse(input_path)
    
    # Process based on mode
    if mode == 'anonymize':
        # De-identify the content
        logger.info("De-identifying content...")
        processed_content, replacements = deidentifier.anonymize(pdf_content)
        
        # Save the mappings
        mappings_file = output_dir / f"{Path(input_path).stem}_mappings.json"
        save_json(replacements, mappings_file)
        
    else:  # deanonymize mode
        if not mappings_path:
            raise ValueError("Mappings file required for deanonymize mode")
            
        # Load the mappings
        mappings = load_json(mappings_path)
        
        # Re-identify the content
        logger.info("Re-identifying content...")
        processed_content = deidentifier.deanonymize(pdf_content, mappings)
        mappings_file = None
    
    # Save the processed content
    output_file = output_dir / f"{Path(input_path).stem}_processed.{output_format}"
    
    # Convert output_file to string for compatibility with parser.save
    output_file_str = str(output_file)
    
    # Ensure the output file has the correct extension
    if not output_file_str.endswith(f'.{output_format}'):
        output_file_str = f"{output_file_str}.{output_format}"
    
    # Save the processed content
    pdf_parser.save(processed_content, output_file_str)
    
    return output_file_str, str(mappings_file) if mappings_file else None

def main():
    """Main entry point of the script."""
    args = parse_arguments()
    
    # Set log level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists() or not input_path.is_file():
        logger.error(f"Input file does not exist: {input_path}")
        sys.exit(1)
        
    if input_path.suffix.lower() != '.pdf':
        logger.error(f"Input file must be a PDF: {input_path}")
        sys.exit(1)
    
    # Validate mappings for deanonymize mode
    if args.mode == 'deanonymize' and not args.mappings:
        logger.error("Mappings file required for deanonymize mode")
        sys.exit(1)
    
    try:
        # Process the PDF
        output_file, mappings_file = process_pdf(
            str(input_path),
            args.output,
            args.format,
            args.mode,
            args.mappings
        )
        
        logger.info(f"Processing complete. Output file: {output_file}")
        if mappings_file:
            logger.info(f"Mappings saved to: {mappings_file}")
            
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        logger.debug("Exception details:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 