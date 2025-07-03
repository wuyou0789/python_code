#!/usr/bin/env python3

"""
================================================================================
Advanced Video to MP3 Conversion Tool (with JSON Config Support)
================================================================================
Author: AI Assistant (Refined and Refactored)
Date: 2025-07-03
Version: 6.1 (Simplified)

Description:
  A highly configurable, robust, and modern tool to convert videos to MP3s.

New in v6.1:
  - Simplified the conversion logic by removing the temp-file-then-rename
    strategy. The script now writes directly to the final .mp3 file and
    cleans up on failure. This is a good simplification for debugging.
================================================================================
"""
import os
import sys
import json
import argparse
import subprocess
import logging
import re
from pathlib import Path
from shutil import which

# --- Globals and Constants ---
RESOLUTION_PATTERN = re.compile(r'_r(720|480|360|240)P$', re.IGNORECASE)
SUPPORTED_EXTENSIONS = ('.mp4', '.mov', '.mkv', '.avi', '.m4v', '.flv', '.webm')


def setup_logging(logfile: Path = None):
    """Configures the logging system."""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    log_level = logging.INFO
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    if logfile:
        logfile.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=logfile, level=log_level, format=log_format, filemode='a')
    else:
        logging.basicConfig(level=log_level, format=log_format, stream=sys.stdout)


def find_video_files(source_dir: Path, recursive: bool = False):
    """Yields the full path of video files found in the source directory using pathlib."""
    glob_pattern = '**/*' if recursive else '*'
    for filepath in source_dir.glob(glob_pattern):
        if filepath.is_file() and filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield filepath


def clean_filename(base_name: str) -> str:
    """Removes specific resolution tags from a filename using a pre-compiled regex."""
    cleaned_name = RESOLUTION_PATTERN.sub('', base_name)
    if cleaned_name != base_name:
        logging.debug(f"Cleaned filename: '{base_name}' -> '{cleaned_name}'")
    return cleaned_name


def convert_videos_to_mp3(source_dir: Path, output_dir: Path, recursive: bool, bitrate: str, append_extension: bool):
    """
    The main logic for finding and converting video files.
    Writes directly to the final .mp3 file.
    """
    logging.info("Starting conversion process...")
    logging.info(f"Source: {source_dir}, Output: {output_dir}, Recursive: {recursive}, Bitrate: {bitrate}, Append Extension: {append_extension}")
    counters = {'converted': 0, 'skipped': 0, 'failed': 0, 'found': 0}

    try:
        for video_path in find_video_files(source_dir, recursive):
            counters['found'] += 1
            mp3_path = None  # Reset for each loop iteration

            try:
                # --- Path and Filename Construction ---
                relative_path = video_path.parent.relative_to(source_dir)
                final_output_dir = output_dir / relative_path
                cleaned_base_name = clean_filename(video_path.stem)
                
                if append_extension:
                    mp3_filename = f"{cleaned_base_name}_{video_path.suffix[1:].lower()}.mp3"
                else:
                    mp3_filename = f"{cleaned_base_name}.mp3"
                
                mp3_path = final_output_dir / mp3_filename

                # --- Pre-conversion Checks ---
                final_output_dir.mkdir(parents=True, exist_ok=True)

                if mp3_path.exists():
                    logging.debug(f"SKIP: Final MP3 '{mp3_path.name}' already exists.")
                    counters['skipped'] += 1
                    continue
                
                logging.info(f"CONVERTING: '{video_path.name}' -> '{mp3_path.name}'")
                
                # --- FFmpeg Command Execution ---
                command = [
                    "ffmpeg", "-i", str(video_path),
                    "-vn",                      # No video
                    "-c:a", "libmp3lame",       # Use MP3 audio codec
                    "-b:a", bitrate,            # Set audio bitrate
                    "-loglevel", "error",       # Only show errors
                    "-y",                       # Overwrite output file if it exists
                    str(mp3_path)               # <<-- KEY CHANGE: Write directly to final .mp3 path
                ]
                
                subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')

                counters['converted'] += 1
                logging.info(f"SUCCESS: Created '{mp3_path.name}'.")
                
            except subprocess.CalledProcessError as e:
                counters['failed'] += 1
                logging.error(f"FAILURE: Failed to convert '{video_path.name}'.")
                logging.error(f"  FFmpeg Return Code: {e.returncode}")
                logging.error(f"  FFmpeg Error Output: {e.stderr.strip()}")
                
                # <<-- KEY CHANGE: Clean up the incomplete .mp3 file on failure
                if mp3_path and mp3_path.exists():
                    mp3_path.unlink()
                    logging.warning(f"  CLEANUP: Removed incomplete file '{mp3_path.name}'.")
            except Exception as e:
                counters['failed'] += 1
                logging.error(f"UNEXPECTED ERROR while processing '{video_path.name}': {e}")
                if mp3_path and mp3_path.exists():
                    mp3_path.unlink()
                    logging.warning(f"  CLEANUP: Removed incomplete file due to unexpected error.")

    except KeyboardInterrupt:
        logging.warning("\n--- Process interrupted by user (Ctrl+C). Exiting gracefully. ---")
        
    finally:
        logging.info("--- Conversion process finished ---")
        logging.info(f"Summary: Found={counters['found']}, Converted={counters['converted']}, Skipped={counters['skipped']}, Failed={counters['failed']}")


def main():
    # ... The main() function is exactly the same as before, no changes needed ...
    # (I'm omitting it here for brevity, just use the one from the previous version)
    """Parses arguments, loads config, and starts the conversion process."""
    parser = argparse.ArgumentParser(
        description="A robust tool to batch convert video files to MP3.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # Define command-line arguments
    parser.add_argument("-c", "--config", type=Path, help="Path to a JSON configuration file.")
    parser.add_argument("-i", "--input", type=Path, help="Source video directory.")
    parser.add_argument("-o", "--output", type=Path, help="Destination MP3 directory.")
    parser.add_argument("-r", "--recursive", action='store_true', default=None, help="Recursively search for videos.")
    parser.add_argument("-b", "--bitrate", help="Audio bitrate (e.g., '192k').")
    parser.add_argument("-l", "--logfile", type=Path, help="Path to a log file.")
    parser.add_argument("--no-append-extension", dest='append_extension', action='store_false', help="Do NOT append the original video extension to the MP3 filename.")
    
    args = parser.parse_args()

    # --- Configuration Loading ---
    settings = {
        'input_directory': None,
        'output_directory': None,
        'recursive_search': False,
        'bitrate': '192k',
        'log_file': None,
        'append_source_extension': True,
    }

    if args.config:
        try:
            with args.config.open('r') as f:
                config_from_file = json.load(f)
                settings.update(config_from_file)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error: Could not read or parse config file '{args.config}': {e}", file=sys.stderr)
            sys.exit(1)

    if args.input is not None: settings['input_directory'] = args.input
    if args.output is not None: settings['output_directory'] = args.output
    if args.recursive is not None: settings['recursive_search'] = args.recursive
    if args.bitrate is not None: settings['bitrate'] = args.bitrate
    if args.logfile is not None: settings['log_file'] = args.logfile
    if args.append_extension is False: settings['append_source_extension'] = False

    # --- Setup and Validation ---
    setup_logging(Path(settings['log_file']) if settings['log_file'] else None)

    if not which("ffmpeg"):
        logging.critical("FATAL: 'ffmpeg' command not found. Please install ffmpeg and ensure it's in your system's PATH.")
        sys.exit(1)

    if not settings['input_directory'] or not settings['output_directory']:
        logging.critical("FATAL: Input and Output directories are mandatory.")
        sys.exit(1)

    input_dir = Path(settings['input_directory'])
    output_dir = Path(settings['output_directory'])

    if not input_dir.is_dir():
        logging.critical(f"FATAL: Input directory not found or is not a directory: {input_dir}")
        sys.exit(1)

    # --- Run Conversion ---
    try:
        convert_videos_to_mp3(
            source_dir=input_dir,
            output_dir=output_dir,
            recursive=settings['recursive_search'],
            bitrate=settings['bitrate'],
            append_extension=settings['append_source_extension']
        )
    except Exception as e:
        logging.critical(f"A top-level unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
