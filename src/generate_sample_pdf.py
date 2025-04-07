#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate a sample PDF file with PII data for testing the de-identification tool.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from fpdf import FPDF
import pandas as pd
from faker import Faker

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
        description='Generate a sample PDF with PII data for testing.'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='data/input/sample_with_pii.pdf',
        help='Output PDF file path (default: data/input/sample_with_pii.pdf)'
    )
    
    parser.add_argument(
        '--num-records', '-n',
        type=int,
        default=10,
        help='Number of fake records to generate (default: 10)'
    )
    
    return parser.parse_args()

def generate_fake_data(num_records=10):
    """Generate fake PII data for the sample PDF."""
    faker = Faker()
    
    # Create a list to hold the fake data
    data = []
    
    for _ in range(num_records):
        person = {
            'Name': faker.name(),
            'Email': faker.email(),
            'Phone': faker.phone_number(),
            'SSN': f"{faker.random_int(min=100, max=999)}-{faker.random_int(min=10, max=99)}-{faker.random_int(min=1000, max=9999)}",
            'DOB': faker.date_of_birth().strftime('%m/%d/%Y'),
            'Address': faker.address().replace('\n', ', '),
            'Credit Card': f"{faker.random_int(min=1000, max=9999)}-{faker.random_int(min=1000, max=9999)}-{faker.random_int(min=1000, max=9999)}-{faker.random_int(min=1000, max=9999)}",
            'Company': faker.company(),
            'Job Title': faker.job(),
        }
        data.append(person)
    
    return data

def create_pdf_with_pii(data, output_path):
    """Create a PDF file with the generated PII data."""
    # Initialize Faker for generating dates in the footer
    faker = Faker()
    
    # Ensure output directory exists
    output_dir = Path(output_path).parent
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    
    # Create FPDF object
    pdf = FPDF()
    pdf.add_page()
    
    # Set up the PDF
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Sample Document with PII Data", ln=True, align="C")
    pdf.ln(10)
    
    # Add introduction text
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, "This is a sample document containing personally identifiable information (PII) for testing the Document De-Identifier tool. The following sections contain various types of PII that should be detected and anonymized.")
    pdf.ln(10)
    
    # Add a narrative section with PII
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Narrative Section", ln=True)
    pdf.set_font("Arial", "", 12)
    
    person = data[0]
    narrative = f"""
    Jane Doe is a customer who contacted us on January 15, 2023. She provided her email {person['Email']} and phone number {person['Phone']}. 
    
    She lives at {person['Address']} and works at {person['Company']} as a {person['Job Title']}. Her date of birth is {person['DOB']} and her SSN is {person['SSN']}.
    
    For payment, she provided her credit card {person['Credit Card']}, which expires on 05/2025.
    """
    pdf.multi_cell(0, 10, narrative.strip())
    pdf.ln(10)
    
    # Add a table of customer information
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Customer Information Table", ln=True)
    
    # Create the DataFrame table
    df = pd.DataFrame(data)
    
    # Set column widths
    col_widths = {
        'Name': 40,
        'Email': 60,
        'Phone': 40,
        'SSN': 30,
        'DOB': 25,
        'Company': 50
    }
    
    # Get subset of columns that will fit on the page
    table_columns = ['Name', 'Email', 'Phone', 'SSN', 'DOB', 'Company']
    
    # Add table headers
    pdf.set_font("Arial", "B", 10)
    for col in table_columns:
        pdf.cell(col_widths[col], 10, col, border=1)
    pdf.ln()
    
    # Add table data
    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        for col in table_columns:
            # Ensure content fits in cell by truncating if necessary
            content = str(row[col])
            if len(content) > 30:
                content = content[:27] + "..."
            pdf.cell(col_widths[col], 10, content, border=1)
        pdf.ln()
    
    # Add footer with PII
    pdf.ln(20)
    pdf.set_font("Arial", "I", 8)
    footer_text = f"This document was generated for {data[1]['Name']} ({data[1]['Email']}) on {faker.date_this_year().strftime('%m/%d/%Y')}."
    pdf.cell(0, 10, footer_text, ln=True, align="C")
    
    # Output the PDF
    pdf.output(output_path)
    logger.info(f"Generated sample PDF with PII data: {output_path}")

def main():
    """Main entry point of the script."""
    args = parse_arguments()
    
    # Generate fake data
    logger.info(f"Generating {args.num_records} fake records...")
    fake_data = generate_fake_data(args.num_records)
    
    # Create the PDF
    create_pdf_with_pii(fake_data, args.output)
    
    logger.info("Sample PDF generation complete!")

if __name__ == "__main__":
    main() 