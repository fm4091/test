#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CSV Parser module for handling CSV files.
"""

import os
import json
import logging
import csv
import pandas as pd
from typing import Dict, List, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class CSVParser:
    """
    Handles the parsing of CSV files.
    """
    
    def __init__(self, config=None):
        """Initialize the CSV parser with optional configuration."""
        self.config = config or {}
        
    def parse(self, file_path: str) -> Dict:
        """
        Parse a CSV file.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Dictionary containing the extracted content
        """
        logger.info(f"Parsing CSV file: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Read CSV file using pandas
            df = pd.read_csv(file_path)
            
            # Get column names
            columns = list(df.columns)
            
            # Convert to list of dictionaries for easier processing
            rows = df.to_dict(orient='records')
            
            # Convert values to strings for consistent processing
            string_rows = []
            for row in rows:
                string_row = {}
                for k, v in row.items():
                    # Convert to string, handle NaN
                    if pd.isna(v):
                        string_row[k] = ""
                    else:
                        string_row[k] = str(v)
                string_rows.append(string_row)
            
            # Create result structure
            result = {
                "filename": os.path.basename(file_path),
                "path": file_path,
                "columns": columns,
                "rows": string_rows,
                "row_count": len(string_rows),
                "column_count": len(columns)
            }
            
            logger.info(f"Parsed CSV file with {result['row_count']} rows and {result['column_count']} columns")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing CSV file: {str(e)}")
            raise
    
    def save(self, data: Dict, output_path: str) -> None:
        """
        Save the processed CSV data to a file.
        
        Args:
            data: The processed CSV data
            output_path: Path to save the output
        """
        file_extension = Path(output_path).suffix.lower()
        
        if file_extension == '.csv':
            # Convert back to dataframe and save as CSV
            df = pd.DataFrame(data["rows"])
            df.to_csv(output_path, index=False)
            
        elif file_extension == '.json':
            # Save as JSON
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        elif file_extension == '.txt':
            # Save as formatted text
            with open(output_path, 'w') as f:
                # Write header
                f.write(','.join(data["columns"]) + '\n')
                
                # Write rows
                for row in data["rows"]:
                    f.write(','.join([row.get(col, "") for col in data["columns"]]) + '\n')
        else:
            # Default to CSV
            logger.warning(f"Unsupported output format: {file_extension}. Saving as CSV.")
            df = pd.DataFrame(data["rows"])
            csv_path = output_path.rsplit('.', 1)[0] + '.csv'
            df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved processed CSV data to {output_path}") 