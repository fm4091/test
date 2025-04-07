# Document Deidentification Tool

A tool for identifying and redacting sensitive information in various document formats, with a focus on PDF processing.

## Features

- PDF document parsing and processing
- Identification of personally identifiable information (PII)
- Redaction of sensitive data
- Visualization of redacted content
- Web interface for easy document uploading and processing
- Docker support for easy deployment

## Setup

1. Clone the repository:
```bash
git clone https://github.com/fm4091/test.git
cd test
```

2. Use the setup script to create a virtual environment and install dependencies:
```bash
./setup.sh
```

3. Run the application:
```bash
./run_demo.sh
```

Or use Docker:
```bash
docker-compose up --build
```

## Project Structure

- `app.py`: Main web application
- `src/`: Core processing logic
  - `parsers/`: Document parsing modules
  - `deidentifier.py`: PII detection and redaction
  - `visualize_deidentification.py`: Visualization of processed documents
- `templates/`: Web interface templates
- `static/`: CSS and JavaScript files
- `data/`: Input and output directories for document processing

## Usage

1. Access the web interface at http://localhost:5000
2. Upload a document for processing
3. View and download the redacted document

## License

[MIT License](LICENSE) 