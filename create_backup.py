#!/usr/bin/env python3
"""Simple backup script for Discord War Bot."""

import shutil
from datetime import datetime
from pathlib import Path

def create_backup():
    """Create a timestamped backup of the warbot directory."""

    # Get project root
    project_root = Path(__file__).parent
    warbot_dir = project_root / "warbot"
    backups_dir = project_root / "backups"

    # Create backups directory if it doesn't exist
    backups_dir.mkdir(exist_ok=True)

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"backup_{timestamp}"
    backup_path = backups_dir / backup_name

    print(f"Creating backup: {backup_name}")
    print(f"Source: {warbot_dir}")
    print(f"Destination: {backup_path}")

    # Copy entire warbot directory
    shutil.copytree(warbot_dir, backup_path / "warbot")

    print(f"✅ Backup created successfully!")
    print(f"📁 Location: {backup_path}")

    # List data files that were backed up
    data_dir = backup_path / "warbot" / "data"
    if data_dir.exists():
        data_files = list(data_dir.glob("*.json"))
        print(f"\n📊 Data files backed up:")
        for file in data_files:
            size = file.stat().st_size
            print(f"  - {file.name} ({size} bytes)")

    return backup_path

if __name__ == "__main__":
    try:
        backup_path = create_backup()
        print(f"\n✨ Backup complete: {backup_path.name}")
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        raise
