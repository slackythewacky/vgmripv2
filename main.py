import argparse
import asyncio
import os
from urllib.parse import urlparse, unquote, urljoin
import sys
import aiohttp
from lxml import etree
from lxml.cssselect import CSSSelector
from tqdm.asyncio import tqdm_asyncio
from aiohttp.client_exceptions import ClientConnectorError, ClientResponseError

# Exponential backoff settings
MAX_RETRIES = 5
START_DELAY = 1  # Initial delay in seconds
FACTOR = 2  # Factor to increase delay
JITTER = 1  # Jitter factor

# Function to download a file from a given URL
async def download_file(
    url: str, session: aiohttp.ClientSession, output_folder: str, downloaded_files: set
) -> None:
    # Check if the file has already been downloaded
    if url in downloaded_files:
        return

    try:
        async with session.get(url, ssl=False) as response:  # Disabling SSL certificate verification
            # Parse filename from content disposition header or URL
            if "content-disposition" in response.headers:
                header = response.headers["content-disposition"]
                filename = header.split("filename=")[1]
            else:
                filename = url.split("/")[-1]

            filename = unquote(filename)
            filepath = os.path.join(output_folder, filename)

            # Check if file already exists locally
            if os.path.exists(filepath):
                downloaded_files.add(url)
                return filepath

            # Get the total file size
            total_size = int(response.headers.get("content-length", 0))

            # Write file chunks to disk
            with open(filepath, mode="wb") as file:
                # Use tqdm for progress bar
                progress_bar = tqdm_asyncio(
                    total=total_size, unit="B", unit_scale=True, desc=filename, leave=False
                )
                async for chunk in response.content.iter_any():
                    file.write(chunk)
                    progress_bar.update(len(chunk))
                progress_bar.close()

            # Add URL to set of downloaded files
            downloaded_files.add(url)
            return filepath
    except (ClientConnectorError, ClientResponseError) as e:
        print(f"Failed to download {url}: {e}")
        raise

# CSS selector for downloading links
DOWNLOAD_LINK_SELECTOR = CSSSelector(".songDownloadLink")

# Function to process download page for an album
async def process_download_page(
    url: str, session: aiohttp.ClientSession, output_folder: str, html_parser: etree.HTMLParser, prefer_flac: bool, downloaded_files: set
) -> None:
    try:
        async with session.get(url, ssl=False) as resp:  # Disabling SSL certificate verification
            download_doc = etree.fromstring(await resp.text(), html_parser)
    except aiohttp.ClientError as err:
        raise

    # Extract audio links from download page
    audio_links = {
        y[y.rindex(".") + 1 :]: y
        for y in (
            x.getparent().get("href") for x in DOWNLOAD_LINK_SELECTOR(download_doc)
        )
    }

    # Choose preferred format (FLAC or MP3)
    if prefer_flac and "flac" in audio_links:
        audio_link = audio_links["flac"]
    else:
        audio_link = audio_links["mp3"]

    # Download the file
    return await download_file(audio_link, session, output_folder, downloaded_files)

# CSS selector for album information
INFO_SELECTOR = CSSSelector('p[align="left"]')
# CSS selector for download pages
DOWNLOAD_PAGE_SELECTOR = CSSSelector("#songlist .playlistDownloadSong")

# Async function to handle main logic
async def async_main(args: argparse.Namespace) -> None:
    def print_if_verbose(*msg: str) -> None:
        print(*msg, file=sys.stderr)

    html_parser = etree.HTMLParser()

    input_items = []

    # Parse input URLs and album names
    for item in args.input:
        if item.startswith("http://") or item.startswith("https://"):
            # Case 1: Input item is a full URL
            input_items.append(item)
        elif os.path.isfile(item):
            # Case 2: Input item is a file containing album URLs or names
            with open(item, "r") as file:
                file_content = file.read()
                split_content = file_content.split()
                input_items.extend(split_content)
        else:
            # Case 3: Input item is an album name
            input_items.append(item)

    # Set to track downloaded files
    downloaded_files = set()

    async with aiohttp.ClientSession(raise_for_status=True, timeout=aiohttp.ClientTimeout(total=120)) as session:
        for input_item in input_items:
            if input_item.startswith("http://") or input_item.startswith("https://"):
                # Case 1a: Input item is a full URL
                url = input_item
            else:
                # Case 1b: Input item is an album name
                url = urljoin("https://downloads.khinsider.com/game-soundtracks/album/", input_item)

            # Discover album name from URL
            album_name = os.path.basename(url)
            album_name = album_name.replace("-", " ").title()  # Convert to title case without dashes
            output_folder = os.path.join(os.getcwd(), album_name)
            os.makedirs(output_folder, exist_ok=True)

            try:
                async with session.get(url, ssl=False) as resp:  # Disabling SSL certificate verification
                    print_if_verbose("Obtained list URL...")
                    album_doc = etree.fromstring(await resp.text(), html_parser)
            except aiohttp.ClientError as err:
                raise
            print_if_verbose("Obtained URL for ", album_doc.findtext(".//h2"))
            info_paragraph = etree.tostring(
                INFO_SELECTOR(album_doc)[0], method="text", encoding="unicode"
            ).splitlines()
            for line in info_paragraph:
                if "Number of Files" in line:
                    track_count = int(line.split(":")[-1])
                    break
            print_if_verbose(f"{track_count} songs available")

            download_page_urls = [
                urljoin(
                    url,
                    min(x.get("href") for x in download_page_url.findall("a")),
                )
                for download_page_url in DOWNLOAD_PAGE_SELECTOR(album_doc)
            ]

            if args.perpendicular:
                for download_page_url in download_page_urls:
                    await process_download_page(
                        download_page_url,
                        session,
                        output_folder,
                        html_parser,
                        args.prefer_flac,
                        downloaded_files
                    )
            else:
                download_tasks = [
                    process_download_page(
                        download_page_url,
                        session,
                        output_folder,
                        html_parser,
                        args.prefer_flac,
                        downloaded_files
                    )
                    for download_page_url in download_page_urls
                ]

                downloaded_files_per_album = await asyncio.gather(*download_tasks)
                print()

                if all(file_path is not None for file_path in downloaded_files_per_album):
                    print(f"Skipping {album_name}, because it is already downloaded.")
                else:
                    last_completed_file = next((file_path for file_path in reversed(downloaded_files_per_album) if file_path is not None), None)
                    if last_completed_file:
                        print(f"Resuming at {os.path.basename(last_completed_file)}", end="\r", flush=True)

# Main function to run the asyncio event loop
def main(args: argparse.Namespace) -> None:
    asyncio.run(async_main(args))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="ripvgm",
        description="Automatically download full albums from KHInsider",
        epilog="Written by Red Eye Inc.",
    )

    parser.add_argument("input", nargs="+", help="List of album URLs, names, or paths to files containing URLs or names")
    parser.add_argument("-F", "--prefer-flac", action="store_true", help="Download FLAC files instead of MP3 if available")
    parser.add_argument("-Pe", "--perpendicular", action="store_true", help="Download albums perpendicular to each other (one at a time)")
    parser.add_argument("-Pa", "--parallel", action="store_true", help="Download albums in parallel (default)")

    args = parser.parse_args()

    main(args)
