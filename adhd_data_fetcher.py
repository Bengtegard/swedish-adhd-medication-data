"""
ADHD medication data fetcher from Swedish National Board of Health and Welfare API with logging.

This module provides functionality to fetch ADHD medication prescription data
from the Swedish Social Board's API (Socialstyrelsen).
"""

import json
import csv
import re
import itertools
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def setup_logging(
    log_level: str = "INFO", 
    log_file: Optional[str] = None
) -> None:
    """Setup logging configuration."""
    log_format = "{asctime} - {levelname} - {message}"
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers,
        style= "{",
        force=True  
    )

logger = logging.getLogger(__name__)


# Constants
BASE_RESULT_URL = "https://sdb.socialstyrelsen.se/api/v1/sv/lakemedel/resultat/matt/2"

ATC_CODES = {
    "C02AC02": "Guanfacin",
    "N06BA12": "Lisdexamfetamin", 
    "N06BA09": "Atomoxetin",
    "N06BA04": "Metylfenidat",
    "N06BA02": "Dexamfetamin"
}


# Mappings from Socialstyrelsens metadata
REGION_MAP = {
    1: "Stockholm", 3: "Uppsala", 4: "Södermanland", 5: "Östergötland",
    6: "Jönköping", 7: "Kronoberg", 8: "Kalmar", 9: "Gotland",
    10: "Blekinge", 12: "Skåne", 13: "Halland", 14: "Västra Götaland", 
    17: "Värmland", 18: "Örebro", 19: "Västmanland", 20: "Dalarna",
    21: "Gävleborg", 22: "Västernorrland", 23: "Jämtland Härjedalen",
    24: "Västerbotten", 25: "Norrbotten", 0: "Riket",
}

KON_MAP = {1: "Män", 2: "Kvinnor", 3: "Båda könen"}
ALDER_MAP = {1: "0-4", 2: "5-9", 3: "10-14", 4: "15-19"}

# Default filter values
DEFAULT_REGIONS = list(range(0, 26))  # All regions (0 = Riket, 1-25 = län)
DEFAULT_AGE_GROUPS = [1, 2, 3, 4]     # Age 0-19
DEFAULT_GENDERS = [1, 2, 3]           # Men, Women and Both gender
DEFAULT_YEARS = list(range(2006, 2025))  # Years 2006–2024


def create_session() -> requests.Session:
    """Create requests session with retry strategy."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def _build_api_url(
    atc_code: str, 
    regions: List[int], 
    age_groups: List[int], 
    genders: List[int], 
    years: List[int]
) -> str:
    """
    Build the API URL with specified filters.
    
    Args:
        atc_code: ATC code for the medication
        regions: List of region codes
        age_groups: List of age group codes
        genders: List of gender codes
        years: List of years
        
    Returns:
        Complete API URL string
    """
    region_str = ','.join(map(str, regions))
    age_str = ','.join(map(str, age_groups))
    gender_str = ','.join(map(str, genders))
    year_str = ','.join(map(str, years))
    
    url = (f"{BASE_RESULT_URL}/atc/{atc_code}/region/{region_str}/"
            f"alder/{age_str}/kon/{gender_str}/ar/{year_str}")
    
    logger.debug(f"Built URL: {url}")
    return url


def _fetch_paginated_data(
    session: requests.Session,
    initial_url: str, 
    headers: Optional[Dict[str, str]] = None
) -> List[Dict]:
    """
    Fetch all data from a paginated API endpoint.
    
    Args:
        initial_url: Starting URL for the API request
        headers: Optional HTTP headers
        
    Returns:
        List of all data records from all pages
        
    Raises:
        requests.RequestException: If API request fails
    """
    if headers is None:
        headers = {"Accept": "application/json"}
    
    all_data = []
    url = initial_url
    page = 1

    while url:
        logger.debug(f"Fetching page{page}")

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data_json = response.json()
            
            page_data = data_json.get("data", [])
            # Add data records from current page
            all_data.extend(page_data)
            
            logger.debug(f"Page {page}: {len(page_data)} records")

            # Get next page URL (Swedish: "nästa_sida")
            url = data_json.get("nasta_sida")
            page += 1
            
        except requests.RequestException as e:
            logger.error(f"Request failed on page {page}: {e}")
            raise

    logger.info(f"Fetched {len(all_data)} records across {page-1} pages")
    return all_data


def parse_number(
    s: Optional[str]
) -> Optional[float]:
    """Convert Socialstyrelsen values to float (or None)."""
    if s is None:
        return None
    s = re.sub(r"[\u00A0\s]+", "", str(s))
    s = s.replace(",", ".")
    if s == "" or s.lower() in ("na", "n/a", "-", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        logger.warning(f"Could not parse number: '{s}'")
        return None


def fetch_adhd_medication_data(
    regions: Optional[List[int]] = None,
    age_groups: Optional[List[int]] = None,
    genders: Optional[List[int]] = None,
    years: Optional[List[int]] = None,
    atc_codes: Optional[Dict[str, str]] = None
) -> Dict[str, List[Dict]]:
    """
    Fetch ADHD medication prescription data from Swedish Social Board API.
    
    Args:
        regions: List of region codes (default: all regions 0-25)
        age_groups: List of age group codes (default: [1,2,3,4] for ages 0-19)
        genders: List of gender codes (default: [1,2,3] for men, women, both)
        years: List of years (default: 2006-2025)
        atc_codes: Dict of ATC codes to medication names (default: ADHD medications)
        
    Returns:
        Dictionary with medication names as keys and prescription data as values
        
    Raises:
        requests.RequestException: If API requests fail
    """
    # Use defaults if not provided
    regions = regions or DEFAULT_REGIONS
    age_groups = age_groups or DEFAULT_AGE_GROUPS
    genders = genders or DEFAULT_GENDERS
    years = years or DEFAULT_YEARS
    atc_codes = atc_codes or ATC_CODES

    logger.info(f"Starting fetch for {len(atc_codes)} medications, "
                f"{len(years)} years ({min(years)}-{max(years)})")
    
    results = {}
    session = create_session()
    
    try:
        for atc_code, medication_name in atc_codes.items():
            logger.info(f"Fetching data for {medication_name} ({atc_code})...")
            
            try:
                url = _build_api_url(atc_code, regions, age_groups, genders, years)
                medication_data = _fetch_paginated_data(session, url)
                results[medication_name] = medication_data
                
                logger.info(f"Successfully fetched {len(medication_data)} records for {medication_name}")
                
            except requests.RequestException as e:
                logger.error(f"Failed to fetch data for {medication_name}: {e}")
                # Continue with other medications even if one fails
                continue
                
    finally:
        session.close()
    
    total_records = sum(len(data) for data in results.values())
    logger.info(f"Fetch completed: {total_records:,} total records")
    
    return results


def convert_json_to_csv(
    input_json: str = "adhd_medication_2006-2024.json",
    output_csv: str = "adhd_medication_flat.csv",
) -> None:
    """Convert ADHD medication data from JSON to flattened CSV."""
    logger.info(f"Converting {input_json} to {output_csv}")
    
    try:
        with open(input_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        logger.info(f"Loaded {len(data)} medications from JSON")
        
        # Extract unique values from actual data instead of defaults
        all_years = set()
        all_regions = set()
        all_genders = set()
        all_ages = set()
        
        for records in data.values():
            for record in records:
                all_years.add(record["ar"])
                all_regions.add(record["regionId"])
                all_genders.add(record["konId"])
                all_ages.add(record["alderId"])
        
        # Convert to sorted lists
        data_years = sorted(all_years)
        data_regions = sorted(all_regions)
        data_genders = sorted(all_genders)
        data_ages = sorted(all_ages)
        
        logger.info(f"Data spans: {min(data_years)}-{max(data_years)}, "
                   f"{len(data_regions)} regions, {len(data_ages)} age groups")
        
        with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile, delimiter=";")
            writer.writerow([
                "År", "Läkemedel", "Region", "Kön", "Ålder", "Patienter/1000 invånare"
            ])
            
            rows_written = 0
            
            for med_name, records in data.items():
                if not records:
                    logger.warning(f"No records found for {med_name}")
                    continue
                
                logger.debug(f"Processing {med_name}: {len(records)} records")
                
                # Index existing records
                record_map = {
                    (r["ar"], r["regionId"], r["konId"], r["alderId"]): r
                    for r in records
                }
                
                sample_atc = records[0]["atcId"] if records else ""
                
                # Loop over combinations FROM YOUR DATA, not defaults
                for ar, region_id, kon_id, alder_id in itertools.product(
                    data_years, data_regions, data_genders, data_ages
                ):
                    r = record_map.get((ar, region_id, kon_id, alder_id), None)
                    varde_raw = r.get("varde") if r else None
                    patienter_per_1000 = parse_number(varde_raw)
                    
                    writer.writerow([
                        ar,
                        f"{sample_atc} {med_name}",
                        REGION_MAP[region_id],
                        KON_MAP[kon_id],
                        ALDER_MAP[alder_id],
                        "0" if patienter_per_1000 is None else (
                            f"{patienter_per_1000:.3f}".rstrip("0").rstrip(".")
                        ),
                    ])
                    rows_written += 1
            
            logger.info(f"CSV saved: {output_csv} ({rows_written:,} rows)")
            
    except FileNotFoundError:
        logger.error(f"Input file not found: {input_json}")
        raise
    except Exception as e:
        logger.error(f"Error converting to CSV: {e}")

def save_to_json(
    data: Dict[str, List[Dict]], 
    filename: str = "adhd_medication_2006-2024.json"
) -> None:
    """Save raw data to JSON file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        total_records = sum(len(records) for records in data.values())
        logger.info(f"JSON saved: {filename} ({total_records:,} records)")
        
    except Exception as e:
        logger.error(f"Error saving JSON {filename}: {e}")
        raise


def validate_data(data: Dict[str, List[Dict]]) -> bool:
    """Basic validation of fetched data."""
    if not data:
        logger.error("No data fetched")
        return False
    
    total_records = sum(len(records) for records in data.values())
    if total_records == 0:
        logger.error("All medication datasets are empty")
        return False
    
    # Check each medication has some data
    for med_name, records in data.items():
        if not records:
            logger.warning(f"No records for {med_name}")
        else:
            logger.info(f"{med_name}: {len(records)} records")
            
            # Check for required fields in first record
            if records:
                sample_record = records[0]
                required_fields = ["ar", "regionId", "konId", "alderId", "varde"]
                missing_fields = [field for field in required_fields 
                                if field not in sample_record]
                if missing_fields:
                    logger.warning(f"{med_name} missing fields: {missing_fields}")
    
    logger.info(f"Validation completed: {total_records:,} total records")
    return True


def main() -> None:
    """Main function with logging."""
    # Setup logging
    setup_logging(log_level="INFO", log_file="adhd_fetcher.log")
    
    logger.info("ADHD Medication Data Fetcher Started")
    
    try:
        # Fetch all data
        logger.info("Starting full data fetch...")
        data = fetch_adhd_medication_data()
        
        # Validate data
        if not validate_data(data):
            logger.error("Data validation failed")
            return
        
        # Save files
        save_to_json(data)
        convert_json_to_csv()
        
        logger.info("Process completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Process failed: {e}")
        raise


if __name__ == "__main__":
    main()
