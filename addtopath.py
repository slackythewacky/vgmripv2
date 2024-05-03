#!/usr/bin/env python3

import os
import shutil

def main():
    print("Adding main script to system path...")
    
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if main.py exists in the current directory
    main_script = os.path.join(current_dir, "main.py")
    if not os.path.exists(main_script):
        print("Error: main.py not found in the current directory.")
        return
    
    # Get the directory to copy the main script
    target_dir = "/usr/local/bin"
    target_script = os.path.join(target_dir, "vgmrip")
    
    # Copy the main script to the target directory
    shutil.copy(main_script, target_script)
    
    # Make the script executable
    os.chmod(target_script, 0o755)
    
    # Add shebang line to the copied script
    with open(target_script, "r+") as file:
        content = file.read()
        file.seek(0, 0)
        file.write("#!/usr/bin/env python3\n" + content)
    
    print("Main script successfully added to system path as vgmrip.")

if __name__ == "__main__":
    main()
