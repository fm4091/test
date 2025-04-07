#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document De-Identifier: A tool for ingesting documents in various formats 
and de-identifying personally identifiable information (PII).
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Import internal modules
from parsers.pdf_parser import PDFParser
from parsers.csv_parser import CSVParser
from parsers.text_parser import TextParser
from deidentifier import Deidentifier

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
        description='De-identify documents containing PII data.'
    )
    
    parser.add_argument(
        '--input', '-i', 
        type=str, 
        required=True,
        help='Path to input file or directory'
    )
    
    parser.add_argument(
        '--output', '-o', 
        type=str, 
        required=True,
        help='Path to output directory'
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
        '--config',
        type=str,
        help='Path to config file (optional)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()

def get_parser_for_file(file_path):
    """Returns the appropriate parser based on file extension."""
    extension = Path(file_path).suffix.lower()
    
    if extension in ['.pdf']:
        return PDFParser()
    elif extension in ['.csv']:
        return CSVParser()
    elif extension in ['.txt', '.md', '.json', '.html', '.xml']:
        return TextParser()
    else:
        raise ValueError(f"Unsupported file format: {extension}")

def process_file(file_path, output_dir, deidentifier, mode='anonymize', mappings=None):
    """Process a single file."""
    logger.info(f"Processing file: {file_path}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the appropriate parser for the file
    parser = get_parser_for_file(file_path)
    
    # Parse the file
    parsed_content = parser.parse(file_path)
    
    # Process the content based on mode
    if mode == 'anonymize':
        # De-identify the content
        processed_content, replacements = deidentifier.anonymize(parsed_content)
        
        # Save the replacements to a JSON file
        mapping_file = os.path.join(
            output_dir, 
            Path(file_path).stem + "_mappings.json"
        )
        with open(mapping_file, 'w') as f:
            json.dump(replacements, f, indent=2)
            
        logger.info(f"Saved replacement mappings to {mapping_file}")
        
    else:  # deanonymize mode
        if not mappings:
            raise ValueError("Mappings file required for deanonymize mode")
            
        # Re-identify the content
        processed_content = deidentifier.deanonymize(parsed_content, mappings)
    
    # Save the processed content
    output_file = os.path.join(
        output_dir, 
        Path(file_path).stem + "_processed" + Path(file_path).suffix
    )
    
    # Use the parser to save the processed content
    parser.save(processed_content, output_file)
    
    logger.info(f"Saved processed file to {output_file}")
    return output_file

def main():
    """Main entry point of the application."""
    args = parse_arguments()
    
    # Set log level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize the de-identifier
    deidentifier = Deidentifier(config_path=args.config)
    
    # Check if input is a file or directory
    input_path = Path(args.input)
    output_dir = Path(args.output)
    
    # Load mappings if in deanonymize mode
    mappings = None
    if args.mode == 'deanonymize':
        if not args.mappings:
            logger.error("Mappings file required for deanonymize mode")
            sys.exit(1)
        
        with open(args.mappings, 'r') as f:
            mappings = json.load(f)
    
    # Process files
    if input_path.is_file():
        process_file(
            str(input_path), 
            str(output_dir), 
            deidentifier, 
            args.mode, 
            mappings
        )
    elif input_path.is_dir():
        # Process all files in the directory
        for file_path in input_path.glob('*'):
            if file_path.is_file():
                try:
                    process_file(
                        str(file_path), 
                        str(output_dir), 
                        deidentifier, 
                        args.mode, 
                        mappings
                    )
                except ValueError as e:
                    logger.warning(f"Skipping {file_path}: {str(e)}")
    else:
        logger.error(f"Input path does not exist: {input_path}")
        sys.exit(1)
        
    logger.info("Processing complete")

if __name__ == "__main__":
    main() 