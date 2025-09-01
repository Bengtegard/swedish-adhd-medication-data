"""
Test suite for ADHD medication data fetcher.
Run this before doing the full data fetch.
"""

import unittest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import requests

# Import functions from main script
from adhd_data_fetcher import (
    setup_logging, create_session, _build_api_url,
    parse_number, fetch_adhd_medication_data, validate_data, convert_json_to_csv,
    BASE_RESULT_URL,
)


class TestADHDFetcher(unittest.TestCase):
    """Test cases for ADHD data fetcher functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        setup_logging(log_level="ERROR")  # Suppress logs during tests
        
    def test_parse_number(self):
        """Test number parsing function."""
        # Valid numbers
        self.assertEqual(parse_number("3,44"), 3.44)
        self.assertEqual(parse_number("10.54"), 10.54)
        self.assertEqual(parse_number("0"), 0.0)
        self.assertEqual(parse_number("1234"), 1234.0)
        
        # Invalid/missing values
        self.assertIsNone(parse_number(None))
        self.assertIsNone(parse_number(""))
        self.assertIsNone(parse_number("na"))
        self.assertIsNone(parse_number("N/A"))
        self.assertIsNone(parse_number("-"))
        self.assertIsNone(parse_number("invalid"))
        
        # Edge cases
        self.assertEqual(parse_number(" 5,67 "), 5.67)  # Whitespace
        self.assertEqual(parse_number("0,00"), 0.0)
    
    def test_build_api_url(self):
        """Test API URL building."""
        url = _build_api_url(
            atc_code="N06BA04",
            regions=[0, 1],
            age_groups=[1, 2],
            genders=[1, 2],
            years=[2023]
        )
        
        expected = (
            f"{BASE_RESULT_URL}/atc/N06BA04/region/0,1/"
            f"alder/1,2/kon/1,2/ar/2023"
        )
        self.assertEqual(url, expected)
    
    def test_create_session(self):
        """Test session creation with retry strategy."""
        session = create_session()
        self.assertIsInstance(session, requests.Session)
        
        # Check that adapters are mounted
        self.assertIn("http://", session.adapters)
        self.assertIn("https://", session.adapters)
        session.close()
    
    def test_validate_data(self):
        """Test data validation function."""
        # Valid data
        valid_data = {
            "Metylfenidat": [
                {"ar": 2023, "regionId": 0, "konId": 1, "alderId": 1, "varde": "5.67"}
            ]
        }
        self.assertTrue(validate_data(valid_data))
        
        # Empty data
        self.assertFalse(validate_data({}))
        
        # Empty records
        empty_data = {"Metylfenidat": []}
        self.assertFalse(validate_data(empty_data))


class TestIntegration(unittest.TestCase):
    """Integration tests that actually call the API."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        setup_logging(log_level="ERROR")
    
    def test_api_connection(self):
        """Test that we can connect to the real API."""
        session = create_session()
        
        try:
            # Small test request
            test_url = f"{BASE_RESULT_URL}/atc/N06BA04/region/0/alder/1/kon/3/ar/2023"
            response = session.get(test_url, headers={"Accept": "application/json"}, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.assertIn("data", data)
            
        except requests.RequestException as e:
            self.fail(f"API connection failed: {e}")
        finally:
            session.close()
    
    def test_small_data_fetch(self):
        """Test fetching a small amount of real data."""
        try:
            # Fetch minimal data
            data = fetch_adhd_medication_data(
                regions=[0],  # Just Riket
                years=[2023], # Just 2023  
                atc_codes={"N06BA04": "Metylfenidat"}
            )
            
            self.assertIn("Metylfenidat", data)
            self.assertGreater(len(data["Metylfenidat"]), 0)
            
            # Check record structure
            record = data["Metylfenidat"][0]
            required_fields = ["ar", "regionId", "konId", "alderId"]
            for field in required_fields:
                self.assertIn(field, record)
                
        except Exception as e:
            self.fail(f"Small data fetch failed: {e}")


class TestFileOperations(unittest.TestCase):
    """Test file I/O operations."""
    
    def test_json_save_load(self):
        """Test JSON save and load operations."""
        test_data = {
            "Metylfenidat": [
                {"ar": 2023, "regionId": 0, "konId": 1, "alderId": 1, "varde": "5.67"}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_filename = f.name
        
        try:
            # Test saving
            from adhd_data_fetcher import save_to_json
            save_to_json(test_data, temp_filename)
            
            # Test loading
            with open(temp_filename, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            self.assertEqual(test_data, loaded_data)
            
        finally:
            os.unlink(temp_filename)
    
    def test_csv_conversion(self):
        """Test CSV conversion with mock data."""
        test_data = {
            "Metylfenidat": [
                {
                    "ar": 2023, "regionId": 0, "konId": 1, "alderId": 1, 
                    "varde": "5.67", "atcId": "N06BA04"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as json_file:
            json_filename = json_file.name
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as csv_file:
            csv_filename = csv_file.name
        
        try:
            # Save test data as JSON
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(test_data, f)
            
            # Convert to CSV
            convert_json_to_csv(json_filename, csv_filename)
            
            # Check CSV was created and has content
            self.assertTrue(Path(csv_filename).exists())
            
            with open(csv_filename, 'r', encoding='utf-8') as f:
                csv_content = f.read()
                self.assertIn("År;Läkemedel;Region;Kön;Ålder;Patienter/1000 invånare", csv_content)
                self.assertIn("N06BA04 Metylfenidat", csv_content)
                
        finally:
            os.unlink(json_filename)
            os.unlink(csv_filename)


def run_quick_test() -> bool:
    """Quick connectivity and basic functionality test."""
    print("Running quick connectivity test...")
    
    setup_logging(log_level="INFO")
    
    try:
        # Test API connection
        session = create_session()
        test_url = f"{BASE_RESULT_URL}/atc/N06BA04/region/0/alder/1/kon/3/ar/2023"
        
        response = session.get(test_url, headers={"Accept": "application/json"}, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        session.close()
        
        if "data" not in data:
            print("API returned unexpected format")
            return False
            
        print("API connection successful")
        
        # Test small data fetch
        print("Testing small data fetch...")
        test_data = fetch_adhd_medication_data(
            regions=[0],
            years=[2023],
            atc_codes={"N06BA04": "Metylfenidat"}
        )
        
        if validate_data(test_data):
            print("Small data fetch successful")
            return True
        else:
            print("Data validation failed")
            return False
            
    except Exception as e:
        print(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    # Check for test flag
    if len(sys.argv) > 1 and sys.argv[1] == "--quick-test":
        success = run_quick_test()
        sys.exit(0 if success else 1)
    else:
        main()