#!/bin/bash

# Setup Cron Job for Hard Account Deletion
# This script sets up a daily cron job to run the hard deletion script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Setting up cron job for hard account deletion...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Path to the hard deletion script
HARD_DELETE_SCRIPT="$SCRIPT_DIR/hard_delete_accounts.py"

# Check if the hard deletion script exists
if [ ! -f "$HARD_DELETE_SCRIPT" ]; then
    echo -e "${RED}❌ Error: Hard deletion script not found at $HARD_DELETE_SCRIPT${NC}"
    exit 1
fi

# Make the script executable
chmod +x "$HARD_DELETE_SCRIPT"
echo -e "${GREEN}✅ Made hard deletion script executable${NC}"

# Create a wrapper script that sets up the environment
WRAPPER_SCRIPT="$SCRIPT_DIR/run_hard_deletion.sh"

cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash

# Hard Deletion Cron Job Wrapper
# This script sets up the environment and runs the hard deletion script

# Change to the project directory
cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Activated virtual environment"
fi

# Set Python path
export PYTHONPATH="$PROJECT_DIR:\$PYTHONPATH"

# Run the hard deletion script
echo "🚀 Starting hard account deletion at \$(date)"
python3 "$HARD_DELETE_SCRIPT" --days=30

# Log the completion
echo "✅ Hard account deletion completed at \$(date)"
EOF

# Make the wrapper script executable
chmod +x "$WRAPPER_SCRIPT"
echo -e "${GREEN}✅ Created wrapper script at $WRAPPER_SCRIPT${NC}"

# Create log directory
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
echo -e "${GREEN}✅ Created log directory at $LOG_DIR${NC}"

# Cron job entry (runs daily at 2 AM)
CRON_ENTRY="0 2 * * * $WRAPPER_SCRIPT >> $LOG_DIR/hard_deletion_cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$WRAPPER_SCRIPT"; then
    echo -e "${YELLOW}⚠️ Cron job already exists for hard deletion${NC}"
    echo -e "${BLUE}Current cron jobs:${NC}"
    crontab -l | grep "$WRAPPER_SCRIPT"
else
    # Add the cron job
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo -e "${GREEN}✅ Added cron job: $CRON_ENTRY${NC}"
fi

# Create a test script for manual execution
TEST_SCRIPT="$SCRIPT_DIR/test_hard_deletion.sh"

cat > "$TEST_SCRIPT" << EOF
#!/bin/bash

# Test Hard Deletion Script
# Run this to test the hard deletion process in dry-run mode

echo "🧪 Testing hard deletion script in dry-run mode..."

cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Set Python path
export PYTHONPATH="$PROJECT_DIR:\$PYTHONPATH"

# Run in dry-run mode
python3 "$HARD_DELETE_SCRIPT" --dry-run --days=30

echo "✅ Test completed"
EOF

chmod +x "$TEST_SCRIPT"
echo -e "${GREEN}✅ Created test script at $TEST_SCRIPT${NC}"

# Display setup summary
echo -e "\n${BLUE}📋 Setup Summary:${NC}"
echo -e "${GREEN}✅ Hard deletion script: $HARD_DELETE_SCRIPT${NC}"
echo -e "${GREEN}✅ Wrapper script: $WRAPPER_SCRIPT${NC}"
echo -e "${GREEN}✅ Test script: $TEST_SCRIPT${NC}"
echo -e "${GREEN}✅ Log directory: $LOG_DIR${NC}"
echo -e "${GREEN}✅ Cron job: Runs daily at 2:00 AM${NC}"

echo -e "\n${BLUE}🔧 Usage:${NC}"
echo -e "• Test the script: ${YELLOW}$TEST_SCRIPT${NC}"
echo -e "• Run manually: ${YELLOW}$WRAPPER_SCRIPT${NC}"
echo -e "• View cron jobs: ${YELLOW}crontab -l${NC}"
echo -e "• View logs: ${YELLOW}tail -f $LOG_DIR/hard_deletion_cron.log${NC}"

echo -e "\n${GREEN}🎉 Cron job setup completed successfully!${NC}"
