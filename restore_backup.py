#!/usr/bin/env python3
"""Restore script for Discord War Bot backups."""

import shutil
import sys
from pathlib import Path

def list_backups():
    """List all available backups."""
    project_root = Path(__file__).parent
    backups_dir = project_root / "backups"

    if not backups_dir.exists():
        print("No backups directory found.")
        return []

    backups = sorted([d for d in backups_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")])

    if not backups:
        print("No backups found.")
        return []

    print("\n📦 Available backups:")
    for i, backup in enumerate(backups, 1):
        timestamp = backup.name.replace("backup_", "")
        print(f"  {i}. {timestamp}")

    return backups

def restore_backup(backup_name):
    """Restore a specific backup."""
    project_root = Path(__file__).parent
    backups_dir = project_root / "backups"
    backup_path = backups_dir / backup_name

    if not backup_path.exists():
        print(f"❌ Backup not found: {backup_name}")
        return False

    warbot_backup = backup_path / "warbot"
    if not warbot_backup.exists():
        print(f"❌ Invalid backup: warbot directory not found in {backup_name}")
        return False

    # Create a safety backup of current state first
    print("Creating safety backup of current state...")
    from datetime import datetime
    safety_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safety_backup = backups_dir / f"backup_pre_restore_{safety_timestamp}"

    current_warbot = project_root / "warbot"
    if current_warbot.exists():
        shutil.copytree(current_warbot, safety_backup / "warbot")
        print(f"✅ Safety backup created: {safety_backup.name}")

    # Confirm restore
    print(f"\n⚠️  WARNING: This will replace your current warbot directory!")
    print(f"Restoring from: {backup_name}")
    response = input("Type 'yes' to continue: ")

    if response.lower() != "yes":
        print("❌ Restore cancelled.")
        return False

    # Remove current warbot directory
    if current_warbot.exists():
        shutil.rmtree(current_warbot)

    # Copy backup to current location
    shutil.copytree(warbot_backup, current_warbot)

    print(f"\n✅ Restore complete!")
    print(f"Restored from: {backup_name}")
    print(f"Safety backup: {safety_backup.name}")

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Discord War Bot - Backup Restore Tool")
        print("=" * 50)
        backups = list_backups()

        if backups:
            print("\nUsage:")
            print("  python restore_backup.py <backup_name>")
            print("\nExample:")
            print(f"  python restore_backup.py {backups[-1].name}")
    else:
        backup_name = sys.argv[1]
        if not backup_name.startswith("backup_"):
            backup_name = f"backup_{backup_name}"

        restore_backup(backup_name)
