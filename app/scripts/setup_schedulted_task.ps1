# Setup Windows Scheduled Task for Hard Account Deletion
# This PowerShell script sets up a daily scheduled task to run the hard deletion script

param(
    [string]$TaskName = "AI-Tutor-Hard-Account-Deletion",
    [string]$Time = "02:00"
)

Write-Host "🔧 Setting up Windows Scheduled Task for hard account deletion..." -ForegroundColor Blue

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# Path to the hard deletion script
$HardDeleteScript = Join-Path $ScriptDir "hard_delete_accounts.py"

# Check if the hard deletion script exists
if (-not (Test-Path $HardDeleteScript)) {
    Write-Host "❌ Error: Hard deletion script not found at $HardDeleteScript" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found hard deletion script at $HardDeleteScript" -ForegroundColor Green

# Create a batch file wrapper for the Python script
$BatchWrapper = Join-Path $ScriptDir "run_hard_deletion.bat"

$BatchContent = @"
@echo off
echo 🚀 Starting hard account deletion at %date% %time%

REM Change to the project directory
cd /d "$ProjectDir"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo ✅ Activated virtual environment
)

REM Set Python path
set PYTHONPATH=$ProjectDir;%PYTHONPATH%

REM Run the hard deletion script
python "$HardDeleteScript" --days=30

echo ✅ Hard account deletion completed at %date% %time%
"@

# Write the batch file
$BatchContent | Out-File -FilePath $BatchWrapper -Encoding ASCII
Write-Host "✅ Created batch wrapper at $BatchWrapper" -ForegroundColor Green

# Create log directory
$LogDir = Join-Path $ProjectDir "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
Write-Host "✅ Created log directory at $LogDir" -ForegroundColor Green

# Log file path
$LogFile = Join-Path $LogDir "hard_deletion_scheduled.log"

try {
    # Check if task already exists
    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    
    if ($ExistingTask) {
        Write-Host "⚠️ Scheduled task '$TaskName' already exists" -ForegroundColor Yellow
        Write-Host "Updating existing task..." -ForegroundColor Blue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    
    # Create the scheduled task action
    $Action = New-ScheduledTaskAction -Execute $BatchWrapper -WorkingDirectory $ProjectDir
    
    # Create the scheduled task trigger (daily at specified time)
    $Trigger = New-ScheduledTaskTrigger -Daily -At $Time
    
    # Create task settings
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    
    # Create the principal (run as SYSTEM for reliability)
    $Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    
    # Register the scheduled task
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Daily hard deletion of expired soft-deleted AI Tutor accounts"
    
    Write-Host "✅ Successfully created scheduled task '$TaskName'" -ForegroundColor Green
    Write-Host "   - Runs daily at $Time" -ForegroundColor Green
    Write-Host "   - Executes: $BatchWrapper" -ForegroundColor Green
    
} catch {
    Write-Host "❌ Error creating scheduled task: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Create a test script for manual execution
$TestScript = Join-Path $ScriptDir "test_hard_deletion.bat"

$TestContent = @"
@echo off
echo 🧪 Testing hard deletion script in dry-run mode...

cd /d "$ProjectDir"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Set Python path
set PYTHONPATH=$ProjectDir;%PYTHONPATH%

REM Run in dry-run mode
python "$HardDeleteScript" --dry-run --days=30

echo ✅ Test completed
pause
"@

$TestContent | Out-File -FilePath $TestScript -Encoding ASCII
Write-Host "✅ Created test script at $TestScript" -ForegroundColor Green

# Display setup summary
Write-Host "`n📋 Setup Summary:" -ForegroundColor Blue
Write-Host "✅ Hard deletion script: $HardDeleteScript" -ForegroundColor Green
Write-Host "✅ Batch wrapper: $BatchWrapper" -ForegroundColor Green
Write-Host "✅ Test script: $TestScript" -ForegroundColor Green
Write-Host "✅ Log directory: $LogDir" -ForegroundColor Green
Write-Host "✅ Scheduled task: '$TaskName' (runs daily at $Time)" -ForegroundColor Green

Write-Host "`n🔧 Usage:" -ForegroundColor Blue
Write-Host "• Test the script: $TestScript" -ForegroundColor Yellow
Write-Host "• Run manually: $BatchWrapper" -ForegroundColor Yellow
Write-Host "• View scheduled tasks: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
Write-Host "• View task history: Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-TaskScheduler/Operational'; ID=200,201}" -ForegroundColor Yellow

Write-Host "`n🎉 Scheduled task setup completed successfully!" -ForegroundColor Green
