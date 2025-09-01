#!/bin/bash
# adhd_fetcher_cron.sh

# Set environment variables
export PATH="/home/bengtegard/miniconda3/bin:$PATH"
export PYTHONPATH="/home/bengtegard/src/02_school_ec/08_python/kunskapskontroll_1"

# Change to your project directory
cd /home/bengtegard/src/02_school_ec/08_python/kunskapskontroll_1

# Initialize conda
source /home/bengtegard/miniconda3/etc/profile.d/conda.sh

# Activate virtual environment
conda activate adhd_analysis

# Run the Python script
python adhd_data_fetcher.py >> /home/bengtegard/src/02_school_ec/08_python/kunskapskontroll_1/adhd_fetcher_cron.log 2>&1

# Send email on success
if [ $? -eq 0 ]; then
    echo "ADHD data fetch completed successfully on $(date)" | mail -s "ADHD Data Update - Success" bengtegard
else
    echo "ADHD data fetch FAILED on $(date)" | mail -s "ADHD Data Update - FAILED" bengtegard
fi