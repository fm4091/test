#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Deidentifier module for handling PII recognition and anonymization using Microsoft Presidio.
"""

import os
import json
import logging
import random
import string
from typing import Dict, List, Tuple, Any, Union

# Microsoft Presidio imports
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import RecognizerResult, OperatorConfig

# Faker for generating realistic fake data
from faker import Faker

logger = logging.getLogger(__name__)

class Deidentifier:
    """
    Handles the de-identification of PII in text content using Microsoft Presidio.
    """
    
    def __init__(self, config_path=None):
        """Initialize the Deidentifier with optional configuration."""
        self.config = {}
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        
        # Initialize Faker for generating synthetic data
        self.faker = Faker()
        
        # Set up Presidio Analyzer with NLP engine
        self.nlp_engine = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
            }
        ).create_engine()
        
        # Create the analyzer with our NLP engine
        self.analyzer = AnalyzerEngine(
            nlp_engine=self.nlp_engine,
            registry=RecognizerRegistry(),
            supported_languages=["en"]
        )
        
        # Create the anonymizer
        self.anonymizer = AnonymizerEngine()
        
        # Default PII entities to look for
        self.default_entities = [
            "PERSON", 
            "EMAIL_ADDRESS", 
            "PHONE_NUMBER", 
            "US_SSN", 
            "CREDIT_CARD", 
            "US_BANK_NUMBER",
            "US_DRIVER_LICENSE", 
            "US_PASSPORT", 
            "US_ITIN", 
            "LOCATION", 
            "DATE_TIME", 
            "NRP",
            "IP_ADDRESS", 
            "DOMAIN_NAME", 
            "URL"
        ]
        
        # Get PII entities from config or use defaults
        self.pii_entities = self.config.get("pii_entities", self.default_entities)
        
        logger.info(f"Deidentifier initialized with entities: {self.pii_entities}")
    
    def anonymize(self, content: Union[str, Dict, List]) -> Tuple[Any, Dict]:
        """
        De-identify PII in the content.
        
        Args:
            content: Text content or structured data to anonymize
            
        Returns:
            Tuple of (anonymized_content, replacement_map)
        """
        if isinstance(content, str):
            return self._anonymize_text(content)
        elif isinstance(content, dict):
            return self._anonymize_dict(content)
        elif isinstance(content, list):
            return self._anonymize_list(content)
        else:
            logger.warning(f"Unsupported content type: {type(content)}")
            return content, {}
    
    def _anonymize_text(self, text: str) -> Tuple[str, Dict]:
        """
        Anonymize a text string.
        
        Args:
            text: The text to anonymize
            
        Returns:
            Tuple of (anonymized_text, replacement_map)
        """
        logger.debug(f"Analyzing text: {text[:100]}...")
        
        # Analyze the text to find PII entities
        analyzer_results = self.analyzer.analyze(
            text=text,
            entities=self.pii_entities,
            language="en"
        )
        
        # If no entities found, return the original text
        if not analyzer_results:
            logger.info("No PII entities found in text")
            return text, {}
        
        # Define operators for each entity type
        operators = {
            "PERSON": lambda _: self.faker.name(),
            "EMAIL_ADDRESS": lambda _: self.faker.email(),
            "PHONE_NUMBER": lambda _: self.faker.phone_number(),
            "US_SSN": lambda _: f"XXX-XX-{random.randint(1000, 9999)}",
            "CREDIT_CARD": lambda _: f"XXXX-XXXX-XXXX-{random.randint(1000, 9999)}",
            "US_BANK_NUMBER": lambda _: f"XXXXXXX{random.randint(1000, 9999)}",
            "US_DRIVER_LICENSE": lambda _: f"X{random.randint(10000000, 99999999)}",
            "US_PASSPORT": lambda _: f"X{random.randint(10000000, 99999999)}",
            "US_ITIN": lambda _: f"9XX-XX-{random.randint(1000, 9999)}",
            "LOCATION": lambda _: self.faker.city(),
            "DATE_TIME": lambda _: self.faker.date_time_this_decade().strftime("%Y-%m-%d"),
            "NRP": lambda _: f"XX-{random.randint(1000, 9999)}-XX",
            "IP_ADDRESS": lambda _: self.faker.ipv4(),
            "DOMAIN_NAME": lambda _: self.faker.domain_name(),
            "URL": lambda _: self.faker.url()
        }
        
        # Generate replacement map
        replacement_map = {}
        anonymized_text = text
        
        # Sort results by start index in descending order to replace from end to start
        # This prevents index shifting issues during replacement
        sorted_results = sorted(analyzer_results, key=lambda x: x.start, reverse=True)
        
        for result in sorted_results:
            original_text = text[result.start:result.end]
            entity_type = result.entity_type
            
            # Generate replacement text using the appropriate operator
            if entity_type in operators:
                replacement_text = operators[entity_type](original_text)
            else:
                # For unknown entity types, use a generic replacement
                replacement_text = f"[REDACTED-{entity_type}]"
            
            # Replace the text
            anonymized_text = (
                anonymized_text[:result.start] + 
                replacement_text + 
                anonymized_text[result.end:]
            )
            
            # Add to replacement map
            if entity_type not in replacement_map:
                replacement_map[entity_type] = {}
            
            replacement_map[entity_type][original_text] = replacement_text
            
            logger.debug(f"Replaced {entity_type}: '{original_text}' -> '{replacement_text}'")
        
        return anonymized_text, replacement_map
    
    def _anonymize_dict(self, data: Dict) -> Tuple[Dict, Dict]:
        """Anonymize a dictionary by anonymizing all string values."""
        anonymized_data = {}
        all_replacements = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                anonymized_value, replacements = self._anonymize_text(value)
                anonymized_data[key] = anonymized_value
                
                # Merge replacements
                for entity_type, entity_replacements in replacements.items():
                    if entity_type not in all_replacements:
                        all_replacements[entity_type] = {}
                    all_replacements[entity_type].update(entity_replacements)
                    
            elif isinstance(value, dict):
                anonymized_value, replacements = self._anonymize_dict(value)
                anonymized_data[key] = anonymized_value
                
                # Merge replacements
                for entity_type, entity_replacements in replacements.items():
                    if entity_type not in all_replacements:
                        all_replacements[entity_type] = {}
                    all_replacements[entity_type].update(entity_replacements)
                    
            elif isinstance(value, list):
                anonymized_value, replacements = self._anonymize_list(value)
                anonymized_data[key] = anonymized_value
                
                # Merge replacements
                for entity_type, entity_replacements in replacements.items():
                    if entity_type not in all_replacements:
                        all_replacements[entity_type] = {}
                    all_replacements[entity_type].update(entity_replacements)
            else:
                anonymized_data[key] = value
        
        return anonymized_data, all_replacements
    
    def _anonymize_list(self, data: List) -> Tuple[List, Dict]:
        """Anonymize a list by anonymizing all string items."""
        anonymized_data = []
        all_replacements = {}
        
        for item in data:
            if isinstance(item, str):
                anonymized_item, replacements = self._anonymize_text(item)
                anonymized_data.append(anonymized_item)
                
                # Merge replacements
                for entity_type, entity_replacements in replacements.items():
                    if entity_type not in all_replacements:
                        all_replacements[entity_type] = {}
                    all_replacements[entity_type].update(entity_replacements)
                    
            elif isinstance(item, dict):
                anonymized_item, replacements = self._anonymize_dict(item)
                anonymized_data.append(anonymized_item)
                
                # Merge replacements
                for entity_type, entity_replacements in replacements.items():
                    if entity_type not in all_replacements:
                        all_replacements[entity_type] = {}
                    all_replacements[entity_type].update(entity_replacements)
                    
            elif isinstance(item, list):
                anonymized_item, replacements = self._anonymize_list(item)
                anonymized_data.append(anonymized_item)
                
                # Merge replacements
                for entity_type, entity_replacements in replacements.items():
                    if entity_type not in all_replacements:
                        all_replacements[entity_type] = {}
                    all_replacements[entity_type].update(entity_replacements)
            else:
                anonymized_data.append(item)
        
        return anonymized_data, all_replacements
    
    def deanonymize(self, content: Union[str, Dict, List], mappings: Dict) -> Any:
        """
        Re-identify PII in the content using the provided mappings.
        
        Args:
            content: Anonymized content
            mappings: Dictionary of replacements mapping fake values to original values
            
        Returns:
            Re-identified content
        """
        if isinstance(content, str):
            return self._deanonymize_text(content, mappings)
        elif isinstance(content, dict):
            return self._deanonymize_dict(content, mappings)
        elif isinstance(content, list):
            return self._deanonymize_list(content, mappings)
        else:
            logger.warning(f"Unsupported content type: {type(content)}")
            return content
    
    def _deanonymize_text(self, text: str, mappings: Dict) -> str:
        """
        Re-identify a text string.
        
        Args:
            text: The anonymized text
            mappings: Dictionary of replacements
            
        Returns:
            Re-identified text
        """
        deanonymized_text = text
        
        # Create a reverse mapping from anonymized values to original values
        reverse_mappings = {}
        for entity_type, entity_mappings in mappings.items():
            for original, replacement in entity_mappings.items():
                reverse_mappings[replacement] = original
        
        # Sort replacements by length in descending order to prevent partial replacements
        sorted_replacements = sorted(
            reverse_mappings.items(), 
            key=lambda x: len(x[0]), 
            reverse=True
        )
        
        # Replace all anonymized values with their original values
        for anonymized, original in sorted_replacements:
            deanonymized_text = deanonymized_text.replace(anonymized, original)
            
        return deanonymized_text
    
    def _deanonymize_dict(self, data: Dict, mappings: Dict) -> Dict:
        """Re-identify a dictionary by re-identifying all string values."""
        deanonymized_data = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                deanonymized_data[key] = self._deanonymize_text(value, mappings)
            elif isinstance(value, dict):
                deanonymized_data[key] = self._deanonymize_dict(value, mappings)
            elif isinstance(value, list):
                deanonymized_data[key] = self._deanonymize_list(value, mappings)
            else:
                deanonymized_data[key] = value
        
        return deanonymized_data
    
    def _deanonymize_list(self, data: List, mappings: Dict) -> List:
        """Re-identify a list by re-identifying all string items."""
        deanonymized_data = []
        
        for item in data:
            if isinstance(item, str):
                deanonymized_data.append(self._deanonymize_text(item, mappings))
            elif isinstance(item, dict):
                deanonymized_data.append(self._deanonymize_dict(item, mappings))
            elif isinstance(item, list):
                deanonymized_data.append(self._deanonymize_list(item, mappings))
            else:
                deanonymized_data.append(item)
        
        return deanonymized_data 