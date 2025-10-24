# Minecraft Bedrock Server Update and Backup Python Script

A cross-platform Python script for managing Minecraft Bedrock Server, providing automatic updates and intelligent backup functionality.

## Features

* **Cross-Platform Support**
  * Works on both Windows and Linux
  * Automatically detects platform and handles platform-specific requirements
  * Sets appropriate permissions on Linux automatically

* **Auto Installation**
  * Automatically installs Minecraft Bedrock Server if not present
  * Downloads the correct server version for your platform
  * Handles all setup requirements automatically

* **Smart Backup System**
  * Uses 7zip for efficient compression (falls back to zip if 7zip isn't available)
  * Intelligent duplicate detection prevents redundant backups
  * Content-based hashing ensures only changed files are backed up
  * Preserves important server configurations during updates

* **Server Management**
  * Automatic version checking and updates
  * Preserves server configurations during updates
  * Parallel download system for faster updates
  * Progress bars for long operations

## Requirements

* Python 3.6 or higher
* Required Python packages (automatically installed if missing):
  * `requests`
  * `tqdm`
* Optional but recommended:
  * 7zip (for better compression)

## Installation

1. Clone or download this repository:
```bash
git clone https://github.com/Matthew7577/minecraft-bedrock-update-and-backup.git
cd minecraft-bedrock-update-and-backup
```

2. Run the script:
```bash
python minecraft-bedrock-update-backup.py
```

The script will automatically install any missing dependencies and the Minecraft Bedrock Server if needed.

## Usage

### First Run
On first run, the script will:
1. Check for required dependencies
2. Offer to download and install the Minecraft Bedrock Server
3. Set up the necessary folder structure

### Regular Usage
Simply run the script whenever you want to:
- Check for server updates
- Create a backup
- Install a fresh server

The script will automatically:
1. Create a backup of your current server (if it exists)
2. Check for available updates
3. Download and install updates if available
4. Preserve your server configurations

### Backup System

The script implements a smart backup system that:
- Creates compressed backups in the `backup` folder
- Uses content-based hashing to prevent duplicate backups
- Automatically names backups with timestamps
- Preserves backup history

### Protected Files
During updates, the following files/folders are preserved:
- `config`
- `behavior_packs`
- `resource_packs`
- `allowlist.json`
- `permissions.json`
- `server.properties`

## Troubleshooting

### Linux Users
- Ensure the script has executable permissions:
  ```bash
  chmod +x minecraft-bedrock-update-backup.py
  ```
- The script will automatically set correct permissions for the server executable

### Windows Users
- Ensure Python is added to your PATH
- Run the script from a command prompt or PowerShell window

### Common Issues
1. **7zip not found**: The script will automatically fall back to using ZIP compression
2. **Permission denied**: 
   - Windows: Run as administrator
   - Linux: Use sudo or ensure proper permissions
3. **Download fails**: The script will automatically retry with a backup download source