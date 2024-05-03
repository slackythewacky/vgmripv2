import subprocess

def install_dependencies():
    dependencies = [
        "aiohttp",
        "lxml",
        "tqdm",
    ]

    for dependency in dependencies:
        try:
            print(f"Installing {dependency}...")
            subprocess.check_call(["pip", "install", dependency])
            print(f"{dependency} installed successfully.")
        except Exception as e:
            print(f"Failed to install {dependency}: {e}")

if __name__ == "__main__":
    install_dependencies()
