import os
import sys
import logging
import shutil
import zipfile
import math
import concurrent.futures
import subprocess
import time
import hashlib
import json
from datetime import datetime

def set_executable_permission(file_path):
    """Set executable permission on Linux"""
    if sys.platform == 'linux':
        try:
            current = os.stat(file_path)
            os.chmod(file_path, current.st_mode | 0o111)  # Add executable permission
        except Exception as e:
            print(f"Warning: Could not set executable permissions on {file_path}: {e}")

# Set platform-specific variables
if sys.platform == 'linux':
    BEDROCK_EXECUTABLE = 'bedrock_server'
    CLEAR_SCREEN = 'clear'
    SERVER_PLATFORM = 'linux'
elif sys.platform == 'win32':
    BEDROCK_EXECUTABLE = 'bedrock_server.exe'
    CLEAR_SCREEN = 'cls'
    SERVER_PLATFORM = 'windows'
elif sys.platform == 'darwin':
    print("MacOS does not support Minecraft Bedrock Server.\nExit...")
    time.sleep(2.5)
    exit(1)
else:
    print(f"Unsupported platform: {sys.platform}\nExit...")
    time.sleep(2.5)
    exit(1)

# Ensure requests is installed
try:
    import requests
except ImportError:
    print("Installing required package: requests")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# Ensure tqdm is installed
try:
    from tqdm import tqdm
except ImportError or ModuleNotFoundError:
    print("Installing required package: tqdm")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
    from tqdm import tqdm

os.system(CLEAR_SCREEN)

minecraft_directory = os.path.dirname(os.path.abspath(__file__))

def calculate_folder_hash(items_to_backup):
    """Calculate a hash of the folder contents based on file names, sizes, and modification times"""
    hasher = hashlib.sha256()
    
    for item in sorted(items_to_backup):  # Sort to ensure consistent order
        item_path = os.path.join(minecraft_directory, item)
        if os.path.isfile(item_path):
            stat = os.stat(item_path)
            # Hash file path, size and modification time
            file_info = f"{item}|{stat.st_size}|{stat.st_mtime}".encode()
            hasher.update(file_info)
        elif os.path.isdir(item_path):
            for root, dirs, files in os.walk(item_path):
                for file in sorted(files):  # Sort to ensure consistent order
                    file_path = os.path.join(root, file)
                    stat = os.stat(file_path)
                    # Hash relative path, size and modification time
                    file_info = f"{os.path.relpath(file_path, minecraft_directory)}|{stat.st_size}|{stat.st_mtime}".encode()
                    hasher.update(file_info)
    
    return hasher.hexdigest()

def load_backup_hashes():
    """Load the backup hashes from the JSON file"""
    hash_file = os.path.join(minecraft_directory, "backup", "backup_hashes.json")
    if os.path.exists(hash_file):
        try:
            with open(hash_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_backup_hashes(hashes):
    """Save the backup hashes to the JSON file"""
    hash_file = os.path.join(minecraft_directory, "backup", "backup_hashes.json")
    with open(hash_file, 'w') as f:
        json.dump(hashes, f, indent=2)

def create_backup():
    # Get list of items to backup (excluding script, updater folder, and backup folder)
    excluded_items = {
        os.path.basename(__file__),  # Current script
        'updater',                   # Updater folder
        'backup'                     # Backup folder
    }
    
    try:
        # Get list of items to backup
        items_to_backup = [item for item in os.listdir(minecraft_directory) if item not in excluded_items]

        # Calculate hash of current folder contents
        current_hash = calculate_folder_hash(items_to_backup)
        
        # Load existing backup hashes
        backup_hashes = load_backup_hashes()
        
        # Check if we already have a backup with this hash
        if current_hash in backup_hashes:
            existing_backup = backup_hashes[current_hash]
            if os.path.exists(existing_backup):
                print(f"Skipping backup: Content identical to existing backup at {existing_backup}")
                return existing_backup
            else:
                # If the file doesn't exist anymore, remove it from our hash records
                del backup_hashes[current_hash]
                save_backup_hashes(backup_hashes)

        # Create timestamp for backup file
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # Try to use 7z (external) for faster archiving if available
        seven = shutil.which('7z') or shutil.which('7za') or shutil.which('7zr')
        if seven:
            backup_archive = os.path.join(minecraft_directory, 'backup', f"Backup-{timestamp}.7z")
            print(f"Creating archive with 7z ({seven}): {backup_archive}")
            try:
                # Create list of items to archive
                items_paths = [os.path.join(minecraft_directory, item) for item in items_to_backup]
                # Run 7z directly on the source files
                subprocess.run([seven, 'a', '-t7z', '-m0=LZMA2:d32m:fb32', '-mx=3', '-mmt=on', backup_archive] + items_paths, check=True)
                # Save the hash
                backup_hashes[current_hash] = backup_archive
                save_backup_hashes(backup_hashes)
                print(f"Backup archive created successfully: {backup_archive}")
                return backup_archive
            except subprocess.CalledProcessError as e:
                print(f"7z failed ({e}), falling back to zip method")

        # Fallback: create zip file directly from source files using no compression for speed
        backup_zip = os.path.join(minecraft_directory, "backup", f"Backup-{timestamp}.zip")
        print(f"Creating backup archive: {backup_zip}")
        with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_STORED) as zipf:
            for item in items_to_backup:
                item_path = os.path.join(minecraft_directory, item)
                if os.path.isfile(item_path):
                    zipf.write(item_path, item)
                elif os.path.isdir(item_path):
                    for root, dirs, files in os.walk(item_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, minecraft_directory)
                            zipf.write(file_path, arcname)

        # Save the hash
        backup_hashes[current_hash] = backup_zip
        save_backup_hashes(backup_hashes)
        print(f"Backup archive created successfully: {backup_zip}")
        return backup_zip
            
    except Exception as e:
        print(f"Error creating backup: {e}")
        backup_zip = os.path.join(minecraft_directory, "backup", f"Backup-{timestamp}.zip")
        # Clean up if there was an error
        if os.path.exists(backup_zip):
            os.remove(backup_zip)
        raise

newInstall = False
# Check if bedrock_server executable exists
server_exe = os.path.join(minecraft_directory, BEDROCK_EXECUTABLE)
if not os.path.isfile(server_exe):
    newInstall = True
    user_input = input("Bedrock Server not found. Would you like to download it? (y/n): ")
    if user_input.lower() != 'y':
        print("Server download cancelled.")
        exit(0)
    print("Getting Download Link...")

# Create backup folder if it doesn't exist
backup_folder = os.path.join(minecraft_directory, "backup")
os.makedirs(backup_folder, exist_ok=True)

if not newInstall:
    print("Creating backup of server data...")
    backup_path = create_backup()
    print(f"Backup created at: {backup_path}\n")

URL = "https://www.minecraft.net/en-us/download/server/bedrock/"
BACKUP_URL = "https://raw.githubusercontent.com/ghwns9652/Minecraft-Bedrock-Server-Updater/main/backup_download_link.txt"
DOWNLOAD_LINKS_URL = "https://net-secondary.web.minecraft-services.net/api/v1.0/download/links"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Sakiko/7999.0"}

try:
    response = requests.get(DOWNLOAD_LINKS_URL, headers=HEADERS, timeout=5)
    response_json = response.json()
    
    all_links = response_json['result']['links']
    download_link = None
    
    # Find the appropriate download link for the current platform
    platform_type = 'serverBedrockWindows' if SERVER_PLATFORM == 'windows' else 'serverBedrockLinux'
    for link in all_links:
        if link['downloadType'] == platform_type:
            download_link = link['downloadUrl']
            break
    
    if download_link is None:
        raise Exception("serverBedrockWindows download link not found")

except requests.exceptions.Timeout:
    logging.error("timeout raised, recovering")
    response = requests.get(BACKUP_URL, headers=HEADERS, timeout=5)

    download_link=response.text

# Read local version (if any) and skip update if already up-to-date
version_file = os.path.join(minecraft_directory, 'updater', 'server_version.txt')
os.makedirs(os.path.dirname(version_file), exist_ok=True)
local_version = None
if os.path.isfile(version_file):
    with open(version_file, 'r') as f:
        local_version = f.read().strip()
        if not local_version:  # If file is empty, set to None
            local_version = None

# Show Local version
if local_version is None:
    print("No local version found")
else:
    print(f"Local server version {local_version}")

# Extract version from download link
import re
version_match = re.search(r'bedrock-server-(\d+\.\d+\.\d+\.\d+)', download_link)
version = version_match.group(1) if version_match else "unknown"
print(f"Download link (version {version}):", download_link)


if not newInstall and local_version and local_version == version:
    print(f"Local server version {local_version} is up to date. No update needed.")
    # ensure download link file exists/updated
    download_link_file = os.path.join(minecraft_directory, 'updater', 'download_link.txt')
    with open(download_link_file, 'w') as f:
        f.write(download_link)
    sys.exit(0)

logfile = os.path.join(minecraft_directory, 'updater', 'update.log')

resourceDir = os.path.join(minecraft_directory, 'updater', 'resources')
os.makedirs(resourceDir, exist_ok=True)

running_files = os.listdir(resourceDir)

# Function to download a chunk of the file
def download_chunk(args):
    start, end, url = args
    headers = {**HEADERS, 'Range': f'bytes={start}-{end}'}
    response = requests.get(url, headers=headers)
    return start, response.content
# Download server file to resourceDir with version in filename
server_zip = os.path.join(resourceDir, f'bedrock-server-{version}.zip')
print(f"Downloading server version {version} to {server_zip}...")

try:
    # Get file size
    response = requests.head(download_link, headers=HEADERS)
    file_size = int(response.headers.get('content-length', 0))
    
    # Calculate chunk sizes
    chunk_size = 1024 * 1024  # 1MB chunks
    num_chunks = math.ceil(file_size / chunk_size)
    chunks = []
    
    for i in range(num_chunks):
        start = i * chunk_size
        end = min(start + chunk_size - 1, file_size - 1)
        chunks.append((start, end, download_link))
    
    # Download chunks in parallel with progress bar
    with open(server_zip, 'wb') as f:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(download_chunk, chunk) for chunk in chunks]
            
            with tqdm(total=file_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                downloaded = 0
                for future in concurrent.futures.as_completed(futures):
                    start, data = future.result()
                    f.seek(start)
                    f.write(data)
                    downloaded += len(data)
                    pbar.update(len(data))
    
    print("\nDownload completed successfully.")
except Exception as e:
    print(f"Error downloading server: {e}")
    if os.path.exists(server_zip):
        os.remove(server_zip)
    exit(1)

# Create temp directory for extraction
temp_dir = os.path.join(resourceDir, 'temp')
os.makedirs(temp_dir, exist_ok=True)
print(f"Extracting files to temporary directory: {temp_dir}")

# Clear the temp directory if it exists
if os.path.exists(temp_dir):
    for item in os.listdir(temp_dir):
        item_path = os.path.join(temp_dir, item)
        try:
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            print(f"Error clearing temp directory: {e}")

try:
    with zipfile.ZipFile(server_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    print("Files extracted successfully.")

    # Update server files
    print("\nUpdating server files...")

    if newInstall:
        # New install: copy all extracted items into the minecraft directory
        print("New installation detected - copying all files.")
        for item in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, item)
            dst_path = os.path.join(minecraft_directory, item)
            try:
                if os.path.exists(dst_path):
                    if os.path.isfile(dst_path):
                        os.remove(dst_path)
                    else:
                        shutil.rmtree(dst_path)

                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)
                    print(f"Copied: {item}")
                elif os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                    print(f"Copied: {item}/")
            except Exception as e:
                print(f"Error copying {item}: {e}")
    else:
        # Upgrade: preserve configuration and user data
        preserve_items = {
            'config',
            'behavior_packs',
            'resource_packs',
            'allowlist.json',
            'permissions.json',
            'server.properties'
        }

        for item in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, item)
            dst_path = os.path.join(minecraft_directory, item)

            if item not in preserve_items:
                try:
                    if os.path.exists(dst_path):
                        if os.path.isfile(dst_path):
                            os.remove(dst_path)
                        else:
                            shutil.rmtree(dst_path)
                    
                    if os.path.isfile(src_path):
                        shutil.copy2(src_path, dst_path)
                        print(f"Updated: {item}")
                    elif os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path)
                        print(f"Updated: {item}/")
                except Exception as e:
                    print(f"Error updating {item}: {e}")
            else:
                print(f"Preserved: {item}")

    print("\nServer files update completed.")
    # Set executable permissions on Linux
    if sys.platform == 'linux':
        server_executable = os.path.join(minecraft_directory, BEDROCK_EXECUTABLE)
        if os.path.exists(server_executable):
            set_executable_permission(server_executable)
            print(f"Set executable permissions for {BEDROCK_EXECUTABLE}")
    
    # After successful update, write the version and download link
    try:
        version_file = os.path.join(minecraft_directory, 'updater', 'server_version.txt')
        os.makedirs(os.path.dirname(version_file), exist_ok=True)
        with open(version_file, 'w') as vf:
            vf.write(version)

        download_link_file = os.path.join(minecraft_directory, 'updater', 'download_link.txt')
        with open(download_link_file, 'w') as df:
            df.write(download_link)
        
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        print(f"Warning: failed to write version/link files: {e}")
except Exception as e:
    print(f"Error during extraction or update: {e}")
    shutil.rmtree(temp_dir, ignore_errors=True)
    exit(1)
