#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web application for PDF de-identification.
This FastAPI app provides a web interface for uploading PDFs and processing them.
"""

import os
import sys
import uuid
import shutil
import json
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request, Form, Depends
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PDF De-Identifier", 
    description="De-identify personally identifiable information (PII) in PDF documents",
    version="1.0.0"
)

# Create directories for storing files
for dir_path in ["data/input", "data/output", "static", "templates"]:
    os.makedirs(dir_path, exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Dictionary to store job status information
job_status: Dict[str, Dict[str, Any]] = {}

# Helper function to get most recent jobs
def get_recent_jobs(limit: int = 5) -> Dict[str, Dict[str, Any]]:
    """Return the most recent jobs."""
    # Convert to list of tuples, sort, and take top N
    job_items = list(job_status.items())
    job_items.sort(key=lambda x: x[1].get("created_at", 0), reverse=True)
    return dict(job_items[:limit])

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Custom exception handler to render error template."""
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Page Not Found",
                "error_message": "The page you're looking for doesn't exist.",
                "status_code": exc.status_code,
                "back_url": "/"
            },
            status_code=exc.status_code
        )
    
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_title": "Error",
            "error_message": str(exc.detail),
            "status_code": exc.status_code,
            "back_url": "/"
        },
        status_code=exc.status_code
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    logger.exception("Unhandled exception occurred")
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_title": "Server Error",
            "error_message": "An unexpected error occurred on the server.",
            "error_details": str(exc) if app.debug else None,
            "status_code": 500,
            "back_url": "/"
        },
        status_code=500
    )

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page with the upload form."""
    recent_jobs = get_recent_jobs()
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "jobs": recent_jobs,
            "page_title": "PDF De-Identifier"
        }
    )

@app.post("/upload/")
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Handle PDF upload and processing.
    
    Args:
        request: The FastAPI request object
        file: The uploaded PDF file
        background_tasks: FastAPI background tasks for async processing
    
    Returns:
        Redirect to the status page for the submitted job
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Invalid File Type",
                "error_message": "Only PDF files are accepted. Please upload a PDF file.",
                "back_url": "/"
            },
            status_code=400
        )
    
    try:
        # Create a unique job ID
        job_id = str(uuid.uuid4())
        
        # Save the uploaded file
        input_dir = Path("data/input")
        input_path = input_dir / f"{job_id}.pdf"
        
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Get current timestamp
        import time
        timestamp = time.time()
        
        # Update job status
        job_status[job_id] = {
            "status": "processing",
            "original_filename": file.filename,
            "input_path": str(input_path),
            "output_path": None,
            "visualized_path": None,
            "created_at": timestamp,
            "file_size": os.path.getsize(input_path),
            "detected_pii": [],
            "mapping_info": []
        }
        
        # Process in background
        if background_tasks:
            background_tasks.add_task(process_pdf, job_id)
        else:
            # Process immediately if background tasks aren't available
            process_pdf(job_id)
        
        # Redirect to status page
        return {"job_id": job_id, "status": "processing", "redirect": f"/status/{job_id}"}
        
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "Upload Error",
                "error_message": f"An error occurred while processing your upload: {str(e)}",
                "back_url": "/"
            },
            status_code=500
        )

@app.get("/status/{job_id}")
async def get_status(request: Request, job_id: str):
    """
    Get the status of a processing job.
    
    Args:
        request: FastAPI request object
        job_id: The unique job identifier
    
    Returns:
        HTML response with job status information
    """
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_status[job_id]
    
    # If the job is completed, load PII data and mapping info
    if job["status"] == "completed" and not job.get("data_loaded", False):
        try:
            # Get mappings file path
            job_base = Path(job["input_path"]).stem
            mappings_path = Path("data/output") / f"{job_base}_mappings.json"
            
            if mappings_path.exists():
                with open(mappings_path, 'r') as f:
                    mappings_data = json.load(f)
                    
                # Extract detected PII
                job["detected_pii"] = []
                for item in mappings_data.get("deidentified_entities", []):
                    job["detected_pii"].append({
                        "type": item.get("entity_type", "UNKNOWN"),
                        "original_value": item.get("original_text", ""),
                        "redacted_value": item.get("replacement_text", ""),
                        "page": item.get("page", 1)
                    })
                
                # Extract mapping information
                mapping_dict = {}
                for item in mappings_data.get("deidentified_entities", []):
                    key = (item.get("entity_type", "UNKNOWN"), item.get("original_text", ""))
                    if key in mapping_dict:
                        mapping_dict[key]["occurrences"] += 1
                    else:
                        mapping_dict[key] = {
                            "type": key[0],
                            "original": key[1],
                            "replacement": item.get("replacement_text", ""),
                            "occurrences": 1
                        }
                
                job["mapping_info"] = list(mapping_dict.values())
                
                # Create a preview URL if the visualized file exists
                if job.get("visualized_path") and os.path.exists(job["visualized_path"]):
                    job["preview_url"] = f"/download/{job_id}?inline=true"
                
                job["data_loaded"] = True
        except Exception as e:
            logger.error(f"Error loading PII data for job {job_id}: {str(e)}")
    
    return templates.TemplateResponse(
        "status.html", 
        {
            "request": request, 
            "job_id": job_id,
            "job": job_status[job_id]
        }
    )

@app.get("/download/{job_id}")
async def download_processed_pdf(job_id: str, inline: bool = False):
    """
    Download the processed PDF file.
    
    Args:
        job_id: The unique job identifier
        inline: If True, display the PDF inline in browser
    
    Returns:
        The processed PDF file for download
    """
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_status[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Processing not yet complete")
    
    if not job["visualized_path"]:
        raise HTTPException(status_code=404, detail="Processed file not found")
    
    # Return the visualized PDF
    original_filename = job["original_filename"]
    filename_base = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    download_filename = f"{filename_base}_deidentified.pdf"
    
    headers = {}
    if inline:
        headers["Content-Disposition"] = "inline"
    else:
        headers["Content-Disposition"] = f"attachment; filename={download_filename}"
    
    return FileResponse(
        path=job["visualized_path"], 
        filename=download_filename,
        media_type="application/pdf",
        headers=headers
    )

@app.get("/mappings/{job_id}")
async def download_mappings(job_id: str):
    """
    Download the PII mappings JSON file.
    
    Args:
        job_id: The unique job identifier
    
    Returns:
        The mappings JSON file for download
    """
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_status[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Processing not yet complete")
    
    # Get mappings file path
    job_base = Path(job["input_path"]).stem
    mappings_path = Path("data/output") / f"{job_base}_mappings.json"
    
    if not mappings_path.exists():
        raise HTTPException(status_code=404, detail="Mappings file not found")
    
    # Return the mappings JSON
    original_filename = job["original_filename"]
    filename_base = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    download_filename = f"{filename_base}_mappings.json"
    
    return FileResponse(
        path=mappings_path, 
        filename=download_filename,
        media_type="application/json"
    )

def process_pdf(job_id: str):
    """
    Process a PDF file for de-identification.
    
    Args:
        job_id: The unique job identifier
    """
    try:
        logger.info(f"Processing job {job_id}")
        
        if job_id not in job_status:
            logger.error(f"Job {job_id} not found")
            return
        
        job = job_status[job_id]
        input_path = job["input_path"]
        output_dir = Path("data/output")
        
        # Run the de-identification process
        logger.info(f"De-identifying PDF: {input_path}")
        result = subprocess.run([
            "python3", "src/pdf_deidentify.py",
            "--input", input_path,
            "--output", str(output_dir),
            "--format", "json"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"De-identification failed: {result.stderr}")
            job_status[job_id]["status"] = "error"
            job_status[job_id]["error_message"] = result.stderr
            return
        
        # Update the job status with the output file path
        job_base = Path(input_path).stem
        processed_path = output_dir / f"{job_base}_processed.json"
        job_status[job_id]["output_path"] = str(processed_path)
        
        # Generate the visualization
        logger.info(f"Creating visualization for job {job_id}")
        mappings_path = output_dir / f"{job_base}_mappings.json"
        visualized_path = output_dir / f"{job_base}_visualized.pdf"
        
        result = subprocess.run([
            "python3", "src/visualize_deidentification.py",
            "--input", input_path,
            "--mappings", str(mappings_path),
            "--output", str(visualized_path)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Visualization failed: {result.stderr}")
            job_status[job_id]["status"] = "error"
            job_status[job_id]["error_message"] = result.stderr
            return
        
        # Update job status to completed
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["visualized_path"] = str(visualized_path)
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
        job_status[job_id]["status"] = "error"
        job_status[job_id]["error_message"] = str(e)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_redirect():
    """Redirect to docs path with trailing slash to fix assets."""
    return RedirectResponse(url="/docs/")

# Add debug flag for development
app.debug = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")

if __name__ == "__main__":
    # Run the app using Uvicorn when executed directly
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True) 