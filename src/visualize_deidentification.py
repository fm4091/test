#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Visualization tool for PDF de-identification results.
This script creates a visual representation of de-identified fields in a PDF.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
import fitz  # PyMuPDF
import re
from typing import Dict, List, Tuple
import tempfile
import shutil
import subprocess

# Import internal modules
from utils import ensure_dir, load_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Create visualization of de-identified fields in PDFs.'
    )
    
    parser.add_argument(
        '--input', '-i', 
        type=str, 
        required=True,
        help='Path to input PDF file'
    )
    
    parser.add_argument(
        '--mappings', '-m',
        type=str,
        required=True,
        help='Path to mappings JSON file from de-identification'
    )
    
    parser.add_argument(
        '--output', '-o', 
        type=str, 
        default=None,
        help='Path to output PDF file (default: input_visualized.pdf)'
    )
    
    parser.add_argument(
        '--open', 
        action='store_true',
        help='Open the output PDF after creation'
    )
    
    return parser.parse_args()

def find_text_instances(pdf_path: str, target_texts: List[str]) -> List[Tuple[int, fitz.Rect, str]]:
    """
    Find all instances of target texts in the PDF and return their locations.
    
    Args:
        pdf_path: Path to the PDF file
        target_texts: List of text strings to find
        
    Returns:
        List of tuples containing (page_number, rectangle, matching_text)
    """
    # Create regex patterns for each target text
    # We'll escape special characters to ensure exact matching
    patterns = {re.escape(text): text for text in target_texts}
    
    instances = []
    
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    # Search through each page
    for page_num, page in enumerate(doc):
        # For each target text
        for pattern, original_text in patterns.items():
            # Find all matches on the page
            text_instances = page.search_for(original_text)
            
            # Add each instance to our results
            for rect in text_instances:
                instances.append((page_num, rect, original_text))
    
    doc.close()
    return instances

def highlight_text_in_pdf(pdf_path: str, 
                         instances: List[Tuple[int, fitz.Rect, str]], 
                         output_path: str, 
                         color_map: Dict[str, Tuple[float, float, float]]) -> None:
    """
    Create a new PDF with highlighted text.
    
    Args:
        pdf_path: Path to the original PDF
        instances: List of text instances to highlight (page_num, rectangle, text)
        output_path: Path to save the highlighted PDF
        color_map: Mapping of text categories to highlight colors (r,g,b)
    """
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    # Add highlights to each instance
    for page_num, rect, text in instances:
        page = doc[page_num]
        
        # Determine the color based on the content
        color = (1, 0, 0)  # Default: red
        for category, category_color in color_map.items():
            if category.lower() in text.lower():
                color = category_color
                break
        
        # Add the highlight annotation
        highlight = page.add_highlight_annot(rect)
        highlight.set_colors({"stroke": color, "fill": color})
        highlight.set_opacity(0.3)  # Semi-transparent
        highlight.update()
        
        # Add a comment annotation
        comment = page.add_text_annot(
            rect.br,  # Bottom right of the highlight
            f"De-identified {text}",
            icon="Comment"
        )
        comment.set_colors({"stroke": color, "fill": color})
        comment.update()
    
    # Save the result
    doc.save(output_path)
    doc.close()
    
    logger.info(f"Created visualized PDF with {len(instances)} highlighted PII fields: {output_path}")

def open_pdf(pdf_path: str) -> None:
    """Attempt to open a PDF file with the default viewer."""
    try:
        if sys.platform == "win32":
            os.startfile(pdf_path)
        elif sys.platform == "darwin":  # macOS
            subprocess.run(["open", pdf_path], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", pdf_path], check=True)
        logger.info(f"Opened PDF: {pdf_path}")
    except Exception as e:
        logger.warning(f"Could not open PDF: {str(e)}")

def main():
    """Main entry point of the script."""
    args = parse_arguments()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists() or not input_path.is_file():
        logger.error(f"Input file does not exist: {input_path}")
        sys.exit(1)
        
    if input_path.suffix.lower() != '.pdf':
        logger.error(f"Input file must be a PDF: {input_path}")
        sys.exit(1)
    
    # Validate mappings file
    mappings_path = Path(args.mappings)
    if not mappings_path.exists() or not mappings_path.is_file():
        logger.error(f"Mappings file does not exist: {mappings_path}")
        sys.exit(1)
    
    # Set output path if not provided
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_visualized.pdf"
    
    try:
        # Load the mappings file
        logger.info(f"Loading mappings from: {mappings_path}")
        mappings = load_json(mappings_path)
        
        # Extract all original values that were replaced
        original_values = []
        for entity_type, replacements in mappings.items():
            for original, _ in replacements.items():
                original_values.append(original)
        
        logger.info(f"Found {len(original_values)} PII items to visualize")
        
        # Find all instances of these values in the PDF
        logger.info(f"Scanning PDF for PII instances: {input_path}")
        instances = find_text_instances(str(input_path), original_values)
        
        logger.info(f"Found {len(instances)} instances of PII in the PDF")
        
        # Define color map for different entity types
        # Format: (R, G, B) with values from 0 to 1
        color_map = {
            "PERSON": (1, 0, 0),         # Red
            "EMAIL": (0, 0.5, 1),        # Blue
            "PHONE": (0, 0.8, 0),        # Green
            "SSN": (1, 0, 1),            # Magenta
            "CREDIT": (1, 0.65, 0),      # Orange
            "ADDRESS": (0.5, 0, 0.5),    # Purple
            "DATE": (0, 0.5, 0.5),       # Teal
            "COMPANY": (0.6, 0.4, 0.2),  # Brown
        }
        
        # Create highlighted PDF
        highlight_text_in_pdf(
            str(input_path),
            instances,
            str(output_path),
            color_map
        )
        
        # Open the PDF if requested
        if args.open:
            open_pdf(str(output_path))
        
    except Exception as e:
        logger.error(f"Error visualizing de-identification: {str(e)}")
        logger.debug("Exception details:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 