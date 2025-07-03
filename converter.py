#!/usr/bin/env python3

"""
================================================================================
Advanced Video to MP3 Conversion Tool (with JSON Config Support)
================================================================================
Author: AI Assistant (Refined and Refactored)
Date: 2025-07-03
Version: 7.0 (Multi-Task Support)

Description:
  A highly configurable, robust, and modern tool to convert videos to MP3s.

New in v7.0:
  - Added support for defining multiple conversion tasks in the JSON config.
  - The script now iterates through a 'tasks' list in the JSON, applying
    'global_settings' and allowing task-specific overrides.
================================================================================
"""
# --- Imports and Globals are unchanged ---
import os
import sys
import json
import argparse
import subprocess
import logging
import re
from pathlib import Path
from shutil import which

RESOLUTION_PATTERN = re.compile(r'_r(720|480|360|240)P$', re.IGNORECASE)
SUPPORTED_EXTENSIONS = ('.mp4', '.mov', '.mkv', '.avi', '.m4v', '.flv', '.webm')

# --- Helper functions (setup_logging, find_video_files, clean_filename) are unchanged ---
# (Omitted here for brevity, they are the same as the previous version)
def setup_logging(logfile: Path = None):
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    log_level = logging.INFO
    for handler in logging.root.handlers[:]: logging.root.removeHandler(handler)
    if logfile:
        logfile.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=logfile, level=log_level, format=log_format, filemode='a')
    else:
        logging.basicConfig(level=log_level, format=log_format, stream=sys.stdout)

def find_video_files(source_dir: Path, recursive: bool = False):
    glob_pattern = '**/*' if recursive else '*'
    for filepath in source_dir.glob(glob_pattern):
        if filepath.is_file() and filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield filepath

def clean_filename(base_name: str) -> str:
    cleaned_name = RESOLUTION_PATTERN.sub('', base_name)
    if cleaned_name != base_name:
        logging.debug(f"Cleaned filename: '{base_name}' -> '{cleaned_name}'")
    return cleaned_name


# --- The core conversion logic function is unchanged ---
def convert_videos_to_mp3(source_dir: Path, output_dir: Path, recursive: bool, bitrate: str, append_extension: bool):
    logging.info(f"Source: {source_dir}, Output: {output_dir}, Recursive: {recursive}, Bitrate: {bitrate}, Append Extension: {append_extension}")
    counters = {'converted': 0, 'skipped': 0, 'failed': 0, 'found': 0}
    try:
        for video_path in find_video_files(source_dir, recursive):
            counters['found'] += 1
            mp3_path = None
            try:
                relative_path = video_path.parent.relative_to(source_dir)
                final_output_dir = output_dir / relative_path
                cleaned_base_name = clean_filename(video_path.stem)
                if append_extension:
                    mp3_filename = f"{cleaned_base_name}_{video_path.suffix[1:].lower()}.mp3"
                else:
                    mp3_filename = f"{cleaned_base_name}.mp3"
                mp3_path = final_output_dir / mp3_filename
                final_output_dir.mkdir(parents=True, exist_ok=True)
                if mp3_path.exists():
                    logging.debug(f"SKIP: Final MP3 '{mp3_path.name}' already exists.")
                    counters['skipped'] += 1
                    continue
                logging.info(f"CONVERTING: '{video_path.name}' -> '{mp3_path.name}'")
                command = ["ffmpeg", "-i", str(video_path), "-vn", "-c:a", "libmp3lame", "-b:a", bitrate, "-loglevel", "error", "-y", str(mp3_path)]
                subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
                counters['converted'] += 1
                logging.info(f"SUCCESS: Created '{mp3_path.name}'.")
            except subprocess.CalledProcessError as e:
                counters['failed'] += 1
                logging.error(f"FAILURE: Failed to convert '{video_path.name}'.")
                logging.error(f"  FFmpeg Return Code: {e.returncode}")
                logging.error(f"  FFmpeg Error Output: {e.stderr.strip()}")
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
        logging.warning("\n--- Process interrupted by user (Ctrl+C). ---")
    finally:
        logging.info("--- Task finished ---")
        logging.info(f"Task Summary: Found={counters['found']}, Converted={counters['converted']}, Skipped={counters['skipped']}, Failed={counters['failed']}")


# --- The main() function is heavily modified to support multiple tasks ---
def main():
    """Parses arguments, loads config, and iterates through tasks."""
    parser = argparse.ArgumentParser(
        description="A robust tool to batch convert video files to MP3.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-c", "--config", type=Path, required=True, help="Path to a JSON configuration file (now mandatory for multi-task support).")
    args = parser.parse_args()

    # --- Load Configuration ---
    try:
        with args.config.open('r') as f:
            config = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error: Could not read or parse config file '{args.config}': {e}", file=sys.stderr)
        sys.exit(1)

    global_settings = config.get("global_settings", {})
    task_list = config.get("tasks", [])

    # --- Setup and Validation ---
    log_file_path = global_settings.get('log_file')
    setup_logging(Path(log_file_path) if log_file_path else None)

    if not which("ffmpeg"):
        logging.critical("FATAL: 'ffmpeg' command not found. Please install ffmpeg and ensure it's in your system's PATH.")
        sys.exit(1)

    if not task_list:
        logging.critical("FATAL: No 'tasks' found in the configuration file.")
        sys.exit(1)

    logging.info(f"=== Starting Batch Conversion: {len(task_list)} task(s) found ===")

    # --- Loop Through and Run Each Task ---
    for i, task_definition in enumerate(task_list, 1):
        logging.info(f"--- Starting Task {i}/{len(task_list)} ---")
        
        # Merge global settings with task-specific settings
        current_task_settings = global_settings.copy()
        current_task_settings.update(task_definition)

        # Get settings for the current task
        input_dir = current_task_settings.get('input_directory')
        output_dir = current_task_settings.get('output_directory')
        recursive = current_task_settings.get('recursive_search', False)
        bitrate = current_task_settings.get('bitrate', '192k')
        append_ext = current_task_settings.get('append_source_extension', True)

        # Validate settings for the current task
        if not input_dir or not output_dir:
            logging.error(f"SKIPPING Task {i}: 'input_directory' and 'output_directory' are mandatory.")
            continue

        input_path = Path(input_dir)
        output_path = Path(output_dir)

        if not input_path.is_dir():
            logging.error(f"SKIPPING Task {i}: Input directory not found: {input_path}")
            continue

        # Run the conversion for the current task
        try:
            convert_videos_to_mp3(
                source_dir=input_path,
                output_dir=output_path,
                recursive=recursive,
                bitrate=bitrate,
                append_extension=append_ext
            )
        except Exception as e:
            logging.critical(f"A top-level unexpected error occurred during Task {i}: {e}", exc_info=True)

    logging.info("=== Batch Conversion Finished ===")


if __name__ == "__main__":
    main()
