#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF Parser module for extracting text and tables from PDF documents.
"""

import os
import json
import logging
import io
from typing import Dict, List, Any, Tuple, Union
from pathlib import Path

# PDF libraries
import pdfplumber
import tabula
import PyPDF2

logger = logging.getLogger(__name__)

class PDFParser:
    """
    Handles the parsing of PDF documents, including tables.
    """
    
    def __init__(self, config=None):
        """Initialize the PDF parser with optional configuration."""
        self.config = config or {}
        
    def parse(self, file_path: str) -> Dict:
        """
        Parse a PDF file and extract text and tables.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing the extracted content
        """
        logger.info(f"Parsing PDF file: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Create the result structure
        result = {
            "metadata": self._extract_metadata(file_path),
            "pages": []
        }
        
        # Extract text and tables from each page
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                logger.debug(f"Processing page {page_num}")
                
                # Extract tables from the page using tabula
                tables = self._extract_tables(file_path, page_num)
                
                # Extract text from the page using pdfplumber
                text = page.extract_text() or ""
                
                # Add page content to result
                result["pages"].append({
                    "page_num": page_num,
                    "text": text,
                    "tables": tables
                })
        
        logger.info(f"Parsed PDF with {len(result['pages'])} pages")
        return result
    
    def _extract_metadata(self, file_path: str) -> Dict:
        """Extract metadata from the PDF."""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            info = reader.metadata
            
            # Convert PyPDF2 metadata to dict
            metadata = {}
            if info:
                for key, value in info.items():
                    if isinstance(key, str) and key.startswith('/'):
                        key = key[1:]  # Remove leading slash
                    metadata[key] = str(value)
            
            metadata["page_count"] = len(reader.pages)
            
            return metadata
    
    def _extract_tables(self, file_path: str, page_num: int) -> List[Dict]:
        """
        Extract tables from a PDF page using tabula.
        
        Args:
            file_path: Path to the PDF file
            page_num: Page number to extract tables from (1-indexed)
            
        Returns:
            List of dictionaries representing tables with row and column data
        """
        try:
            # Extract tables using tabula
            tables = tabula.read_pdf(
                file_path,
                pages=page_num,
                multiple_tables=True,
                pandas_options={'header': None}
            )
            
            # Convert pandas DataFrames to lists for JSON serialization
            processed_tables = []
            for i, df in enumerate(tables):
                # Replace NaN values with empty strings
                df = df.fillna("")
                
                # Get column names (may be numeric indices if no header)
                columns = [str(col) for col in df.columns]
                
                # Convert to list of dictionaries
                rows = df.to_dict(orient='records')
                
                # Convert each row to have string keys
                string_rows = []
                for row in rows:
                    string_row = {}
                    for k, v in row.items():
                        string_row[str(k)] = str(v) if not isinstance(v, str) else v
                    string_rows.append(string_row)
                
                processed_tables.append({
                    "table_id": i,
                    "columns": columns,
                    "rows": string_rows,
                    "raw_data": df.to_csv(index=False)
                })
            
            return processed_tables
            
        except Exception as e:
            logger.warning(f"Error extracting tables from page {page_num}: {str(e)}")
            return []
    
    def save(self, data: Dict, output_path: str) -> None:
        """
        Save the processed PDF data to a file.
        
        Args:
            data: The processed PDF data
            output_path: Path to save the output
        """
        # For now, save as JSON
        # In a more comprehensive implementation, this could recreate a PDF
        file_extension = Path(output_path).suffix.lower()
        
        if file_extension == '.json':
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        elif file_extension == '.txt':
            # Save as text
            with open(output_path, 'w') as f:
                for page in data["pages"]:
                    f.write(f"--- Page {page['page_num']} ---\n\n")
                    f.write(page["text"])
                    f.write("\n\n")
                    
                    # Write tables
                    for i, table in enumerate(page["tables"]):
                        f.write(f"--- Table {i+1} ---\n")
                        f.write(table["raw_data"])
                        f.write("\n\n")
                        
        elif file_extension == '.pdf':
            # For PDF output, we would need to generate a new PDF
            # This would be more complex and require libraries like reportlab
            # For now, just save as JSON and notify
            logger.warning("PDF output not yet supported. Saving as JSON.")
            json_path = output_path.rsplit('.', 1)[0] + '.json'
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        else:
            # Default to JSON
            logger.warning(f"Unsupported output format: {file_extension}. Saving as JSON.")
            json_path = output_path + '.json'
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
        
        logger.info(f"Saved processed PDF data to {output_path}") 