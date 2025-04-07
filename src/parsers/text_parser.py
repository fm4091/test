#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text Parser module for handling plain text files.
"""

import os
import json
import logging
from typing import Dict, List, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class TextParser:
    """
    Handles the parsing of plain text files.
    """
    
    def __init__(self, config=None):
        """Initialize the text parser with optional configuration."""
        self.config = config or {}
        
    def parse(self, file_path: str) -> Dict:
        """
        Parse a text file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Dictionary containing the extracted content
        """
        logger.info(f"Parsing text file: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read the file content
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Create a simple structure for the content
        result = {
            "filename": os.path.basename(file_path),
            "path": file_path,
            "content": content,
            "line_count": len(content.splitlines())
        }
        
        logger.info(f"Parsed text file with {result['line_count']} lines")
        return result
    
    def save(self, data: Dict, output_path: str) -> None:
        """
        Save the processed text data to a file.
        
        Args:
            data: The processed text data
            output_path: Path to save the output
        """
        file_extension = Path(output_path).suffix.lower()
        
        if file_extension in ['.txt', '.md', '.html', '.xml']:
            # Save as plain text
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(data["content"])
        elif file_extension == '.json':
            # Save as JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        else:
            # Default to text
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(data["content"])
        
        logger.info(f"Saved processed text data to {output_path}") 