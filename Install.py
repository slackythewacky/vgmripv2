import os
import subprocess
from pathlib import Path

def install_dependencies():
    """
    Install required Python packages using subprocess to ensure they are available before import.
    """
    packages = ['requests']
    for package in packages:
        subprocess.check_call(['python3', '-m', 'pip', 'install', package])

# Ensure dependencies are installed before attempting to import them
install_dependencies()

import requests
import zipfile

def download_and_extract_zip(url, extract_to='.'):
    """
    Download a ZIP file from a URL and extract it into the specified directory.
    """
    # Get the file name from the URL
    file_name = url.split('/')[-1]
    local_zip_path = Path(extract_to) / file_name

    # Download the file
    print(f"Downloading {url}...")
    response = requests.get(url)
    response.raise_for_status()  # Raises an HTTPError for bad responses

    # Save the downloaded file
    with open(local_zip_path, 'wb') as f:
        f.write(response.content)

    # Extract the ZIP file
    print(f"Extracting {file_name}...")
    with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    # Clean up the downloaded ZIP file
    os.remove(local_zip_path)

    # Find the directory name in the extracted files
    extracted_dir = zip_ref.namelist()[0].split('/')[0]
    return extracted_dir

def setup_package(extracted_dir):
    """
    Run setup.py from the extracted directory using python3.
    """
    os.chdir(extracted_dir)
    print(f"Running setup.py in {extracted_dir}...")
    subprocess.run(['python3', 'setup.py'], check=True)

def add_to_path():
    """
    Add command to universal program access by running addtopath.py using python3.
    """
    print("Adding to path...")
    subprocess.run(['python3', 'addtopath.py'], check=True)

def main():
    url = "https://github.com/slackythewacky/vgmripv2/archive/refs/heads/main.zip"
    extracted_dir = download_and_extract_zip(url)

    # Setup the package
    setup_package(extracted_dir)

    # Ask user if they want to add the command to the path
    user_choice = input("Would you like to add the command as a universal program? (Y/N) ")
    if user_choice.strip().upper() == 'Y':
        add_to_path()
        print("Installation successful! Try using it now! Type `vgmrip --help`.")
    else:
        print("Bruh, ok I guess you can run main.py yourself then.")

if __name__ == "__main__":
    main()
