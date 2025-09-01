#!/bin/bash
# schedule_annual_fetch.sh
# Automated ADHD medication data fetcher for annual updates
#
# Usage:
# 1. Edit the paths below to match your setup
# 2. Make executable: chmod +x schedule_annual_fetch.sh
# 3. Test: ./schedule_annual_fetch.sh
# 4. Add to crontab: 0 2 15 1 * /path/to/schedule_annual_fetch.sh

# === CONFIGURATION - UPDATE THESE PATHS ===
PROJECT_DIR="/path/to/your/swedish-adhd-medication-data"
PYTHON_ENV="base"  # or your conda environment name
LOG_FILE="$PROJECT_DIR/adhd_fetcher_cron.log"
EMAIL="your-email@example.com"  # optional

# === SETUP ENVIRONMENT ===
# Add conda to PATH (adjust path to your conda installation)
export PATH="$HOME/miniconda3/bin:$PATH"
export PYTHONPATH="$PROJECT_DIR"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Initialize conda
source "$HOME/miniconda3/etc/profile.d/conda.sh"

# Activate environment
conda activate "$PYTHON_ENV"

# === RUN THE FETCHER ===
echo "$(date): Starting ADHD data fetch..." >> "$LOG_FILE"

python adhd_fetcher.py >> "$LOG_FILE" 2>&1

# === CHECK RESULTS AND NOTIFY ===
if [ $? -eq 0 ]; then
    echo "$(date): ADHD data fetch completed successfully" >> "$LOG_FILE"
    
    # Optional: Send success email (requires mail setup)
    if command -v mail &> /dev/null && [ -n "$EMAIL" ]; then
        echo "ADHD medication data updated successfully on $(date)" | \
            mail -s "Swedish ADHD Data Update - Success" "$EMAIL"
    fi
    
    echo "Success: Data updated"
else
    echo "$(date): ADHD data fetch FAILED" >> "$LOG_FILE"
    
    # Optional: Send failure email
    if command -v mail &> /dev/null && [ -n "$EMAIL" ]; then
        echo "ADHD medication data fetch FAILED on $(date). Check logs at $LOG_FILE" | \
            mail -s "Swedish ADHD Data Update - FAILED" "$EMAIL"
    fi
    
    echo "Error: Check $LOG_FILE for details"
    exit 1
fi
