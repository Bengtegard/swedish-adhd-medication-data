# ADHD Medication Data from Socialstyrelsen's API

A simple Python script I built to fetch ADHD medication prescription data from Sweden's National Board of Health and Welfare. Perfect for researchers, students, or anyone curious about ADHD medication trends in Sweden.

## What it does

Downloads prescription data for the 5 main ADHD medications:
- Metylfenidat (Ritalin, Concerta)
- Lisdexamfetamin (Vyvanse) 
- Atomoxetin (Strattera)
- Dexamfetamin (Dexedrine)
- Guanfacin (Intuniv)

Gets you clean data showing patients per 1000 inhabitants by region, age, gender, and year (2006-2024).

## Quick Start

### Requirements
- Python 3.12
- Install dependencies:

```bash
pip install -r requirements.txt

# Download the script
git clone https://github.com/bengtegard/swedish-adhd-medication-data.git
cd swedish-adhd-medication-data

# Install what you need
pip install requests

# Run it
python adhd_data_fetcher.py
```

That's it! You'll get:
- `adhd_medication_2006-2024.json` - Raw data  
- `adhd_medication_flat.csv` - Clean spreadsheet format
- `adhd_fetcher.log` - What happened during the run

## Automation

To automatically receive annual data, use the included cron script.
```bash
# 1. Edit paths in the script
nano schedule_annual_fetch.sh

# 2. Make it executable
chmod +x schedule_annual_fetch.sh

# 3. Test it
./schedule_annual_fetch.sh

# 4. Add to crontab (runs January 15th at 2 AM)
crontab -e
# Add: 0 2 15 1 * /full/path/to/schedule_annual_fetch.sh
```

## Testing a specific sample

```bash
python test_adhd_fetcher.py

## Custom usage

If you want to specify your data:

```python
from adhd_data_fetcher import fetch_adhd_medication_data,
save_to_json, convert_json_to_csv

# Just Stockholm and Skåne, age 15-19, recent years
data = fetch_adhd_medication_data(
    regions=[1, 12],  # Stockholm, Skåne
    years=[2023, 2024],
    age_groups=[4]           # 15-19 age group
)

save_to_json(data, "example_adhd_data.json")

# Convert JSON to CSV
convert_json_to_csv(
    input_json="example_adhd_data.json",
    output_csv="example_adhd_data.csv"
)
```

## The data you get

Your CSV will look like this:
```csv
År;Läkemedel;Region;Kön;Ålder;Patienter/1000 invånare
2023;C02AC02 Guanfacin;Stockholm;Män;15-19;8.45
2023;C02AC02 Guanfacin;Stockholm;Kvinnor;15-19;6.01
2023;C02AC02 Guanfacin;Stockholm;Båda könen;15-19;7.26
2023;C02AC02 Guanfacin;Skåne;Män;15-19;7.99
2023;C02AC02 Guanfacin;Skåne;Kvinnor;15-19;6.43
2023;C02AC02 Guanfacin;Skåne;Båda könen;15-19;7.23
```

Perfect for Excel, R, Python pandas, or whatever you use for analysis.

*Please cite the data as: Läkemedel [Socialstyrelsens statistikdatabas]. Stockholm: Socialstyrelsen. [citerad: YYYY-MM-DD HH:MM]*
## Why I built this

Socialstyrelsen has excellent data, but their website makes it hard to analyze specific medications by ATC code. This tool fixes that.

---

*Data comes from Socialstyrelsen's official API. Läkemedel [Socialstyrelsens statistikdatabas]. Stockholm: Socialstyrelsen. [citerad: 01/09/2025 och 13:37].*
