# Discord War Bot Backups

## About
This directory contains timestamped backups of the entire warbot system before major changes.

## Backup Structure
Each backup is stored in a folder named `backup_YYYY-MM-DD_HH-MM-SS` containing:
- Complete `warbot/` directory with all code
- All data files (`time.json`, `wars.json`, etc.)
- Configuration files

## Current Backups

### backup_2025-10-25_21-46-17
**Created:** October 25, 2025 at 21:46:17
**Reason:** Pre-implementation backup before major warbot redesign
**Contents:**
- Original war system code
- Timer system (with fixed mentions)
- time.json (timer data)
- wars.json (war data)

## How to Restore a Backup

### Method 1: Manual Restore
1. Navigate to the backup folder you want to restore
2. Copy the `warbot/` directory
3. Paste it into the project root, replacing the current `warbot/` directory

### Method 2: Using Restore Script (if available)
```bash
python restore_backup.py backup_2025-10-25_21-46-17
```

## Creating Manual Backups

To create a backup manually:
```bash
cd "C:\Users\Bravo\Documents\Programing Projects\Discord War Tracking Bot"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
mkdir "backups\backup_$timestamp"
cp -r warbot "backups\backup_$timestamp\"
```

## Important Notes
- Always create a backup before major changes
- Keep at least 3-5 recent backups
- Test restore process occasionally to ensure backups work
- Backups do NOT include .env files or bot tokens (by design, for security)
