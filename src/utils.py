#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility functions for the Document De-Identifier.
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Union

logger = logging.getLogger(__name__)

def ensure_dir(directory: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
        
    Returns:
        Path object of the directory
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        dir_path.mkdir(parents=True)
        logger.info(f"Created directory: {dir_path}")
    return dir_path

def save_json(data: Any, file_path: Union[str, Path]) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        file_path: Path to the output file
    """
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved JSON data to {file_path}")

def load_json(file_path: Union[str, Path]) -> Any:
    """
    Load data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Loaded data
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    logger.info(f"Loaded JSON data from {file_path}")
    return data

def get_sample_pdf_path() -> Union[str, None]:
    """
    Find a sample PDF file in the data/input directory.
    
    Returns:
        Path to a sample PDF file, or None if not found
    """
    # Look in the data/input directory for PDF files
    input_dir = Path('data/input')
    if input_dir.exists():
        for file_path in input_dir.glob('*.pdf'):
            return str(file_path)
    
    return None 