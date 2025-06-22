#!/usr/bin/env python3

"""
================================================================================
Advanced Video to MP3 Conversion Tool (with JSON Config Support)
================================================================================
Author: AI Assistant (Refined with user feedback)
Date: 2023-10-27
Version: 5.0

Description:
  A highly configurable tool to convert videos to MP3s. It supports loading
  settings from a JSON config file and can be fine-tuned via command-line.

New in v5.0:
  - Added filename cleaning feature to remove resolution tags (e.g., '_r720P')
    from the output filename, using regular expressions.

... (Previous descriptions) ...
================================================================================
"""
import os
import sys
import json
import argparse
import subprocess
import logging
import re

# ... (setup_logging and find_video_files functions are unchanged) ...
def setup_logging(logfile=None):
    """Configures the logging system."""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    log_level = logging.INFO
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    if logfile:
        logging.basicConfig(filename=logfile, level=log_level, format=log_format, filemode='a')
    else:
        logging.basicConfig(level=log_level, format=log_format, stream=sys.stdout)

def find_video_files(source_dir, recursive=False):
    """Yields the full path of video files found in the source directory."""
    supported_extensions = ('.mp4', '.mov', '.mkv', '.avi', '.m4v', '.flv', '.webm')
    if recursive:
        for root, _, files in os.walk(source_dir):
            for filename in files:
                if filename.lower().endswith(supported_extensions):
                    yield os.path.join(root, filename)
    else:
        for filename in os.listdir(source_dir):
            filepath = os.path.join(source_dir, filename)
            if os.path.isfile(filepath) and filename.lower().endswith(supported_extensions):
                yield filepath

# <<< 新增：文件名清洗辅助函数 >>>
def clean_filename(base_name):
    """
    Removes specific resolution tags from a filename using regex.
    e.g., 'video_r720P' -> 'video'
    """
    # This regex matches '_r' followed by one of the resolutions, then 'P', at the end of the string.
    resolution_pattern = re.compile(r'_r(720|480|360|240)P$', re.IGNORECASE)
    cleaned_name = resolution_pattern.sub('', base_name)
    
    # Log if a change was made
    if cleaned_name != base_name:
        logging.debug(f"Cleaned filename: '{base_name}' -> '{cleaned_name}'")
        
    return cleaned_name


def convert_videos_to_mp3(source_dir, output_dir, recursive, bitrate, append_extension):
    """
    The main logic for finding and converting video files.
    Uses a robust temp-file-then-rename strategy.
    """
    logging.info("Starting conversion process...")
    logging.info(f"Source: {source_dir}, Output: {output_dir}, Recursive: {recursive}, Bitrate: {bitrate}, Append Extension: {append_extension}")
    counters = {'converted': 0, 'skipped': 0, 'failed': 0, 'found': 0}

    # <<< 修改 1：将整个循环包裹在 try...except KeyboardInterrupt 中，以捕获 Ctrl+C >>>
    try:
        for video_filepath in find_video_files(source_dir, recursive):
            counters['found'] += 1
            mp3_filepath = None  # 在循环开始时重置
            mp3_temp_path = None # 在循环开始时重置
            
            try:
                relative_path = os.path.relpath(os.path.dirname(video_filepath), source_dir)
                filename = os.path.basename(video_filepath)
                base_name, orig_ext = os.path.splitext(filename)

                cleaned_base_name = clean_filename(base_name)
                
                if append_extension:
                    mp3_filename = f"{cleaned_base_name}_{orig_ext[1:].lower()}.mp3"
                else:
                    mp3_filename = f"{cleaned_base_name}.mp3"
                
                final_output_dir = os.path.join(output_dir, relative_path) if relative_path != '.' else output_dir
                mp3_filepath = os.path.join(final_output_dir, mp3_filename)
                
                # <<< 修改 2：定义一个临时文件名 >>>
                mp3_temp_path = mp3_filepath + ".tmp"
                
                os.makedirs(final_output_dir, exist_ok=True)

                if os.path.exists(mp3_filepath):
                    logging.debug(f"SKIP: Final MP3 '{mp3_filename}' already exists.")
                    counters['skipped'] += 1
                    continue
                
                # <<< 新增：如果存在上次失败留下的临时文件，先清理掉 >>>
                if os.path.exists(mp3_temp_path):
                    logging.warning(f"CLEANUP: Removing old temporary file '{os.path.basename(mp3_temp_path)}'.")
                    os.remove(mp3_temp_path)

                logging.info(f"CONVERTING: '{filename}' -> '{os.path.basename(mp3_temp_path)}'")
                
                # <<< 修改 3：ffmpeg 命令输出到临时文件 >>>
                command = ["ffmpeg", "-i", video_filepath, "-vn", "-b:a", bitrate, "-loglevel", "error", "-y", mp3_temp_path]
                
                subprocess.run(command, check=True, capture_output=True, text=True)

                # <<< 修改 4：转换成功后，将临时文件重命名为最终文件 >>>
                os.rename(mp3_temp_path, mp3_filepath)
                
                counters['converted'] += 1
                logging.info(f"SUCCESS: Created '{mp3_filename}'.")
                
            except subprocess.CalledProcessError as e:
                logging.error(f"FAILURE: Failed to convert '{video_filepath}'.")
                logging.error(f"  FFmpeg Return Code: {e.returncode}")
                logging.error(f"  FFmpeg Error Output: {e.stderr.strip()}")
                counters['failed'] += 1
                # <<< 修改 5：如果转换失败，清理的是临时文件 >>>
                if mp3_temp_path and os.path.exists(mp3_temp_path):
                    os.remove(mp3_temp_path)
                    logging.warning(f"  CLEANUP: Removed incomplete temporary file '{os.path.basename(mp3_temp_path)}'.")
            except Exception as e:
                logging.error(f"UNEXPECTED ERROR while processing '{video_filepath}': {e}")
                counters['failed'] += 1
                # 如果发生其他异常，也尝试清理临时文件
                if mp3_temp_path and os.path.exists(mp3_temp_path):
                    os.remove(mp3_temp_path)
                    logging.warning(f"  CLEANUP: Removed incomplete temporary file due to unexpected error.")

    except KeyboardInterrupt:
        logging.warning("\n--- Process interrupted by user (Ctrl+C) ---")
        logging.warning("--- Exiting gracefully. ---")
        # 不需要在这里做特殊的清理，因为未完成的文件都是 .tmp 后缀
        
    finally:
        logging.info("--- Conversion process finished ---")
        logging.info(f"Summary: Found={counters['found']}, Converted={counters['converted']}, Skipped={counters['skipped']}, Failed={counters['failed']}")
    """
    The main logic for finding and converting video files.
    """
    logging.info("Starting conversion process...")
    logging.info(f"Source: {source_dir}, Output: {output_dir}, Recursive: {recursive}, Bitrate: {bitrate}, Append Extension: {append_extension}")
    counters = {'converted': 0, 'skipped': 0, 'failed': 0, 'found': 0}

    for video_filepath in find_video_files(source_dir, recursive):
        counters['found'] += 1
        try:
            relative_path = os.path.relpath(os.path.dirname(video_filepath), source_dir)
            filename = os.path.basename(video_filepath)
            base_name, orig_ext = os.path.splitext(filename)

            # === 修改部分：在生成MP3文件名之前先清洗原始文件名 ===
            cleaned_base_name = clean_filename(base_name)
            
            if append_extension:
                mp3_filename = f"{cleaned_base_name}_{orig_ext[1:].lower()}.mp3"
            else:
                mp3_filename = f"{cleaned_base_name}.mp3"
            
            final_output_dir = os.path.join(output_dir, relative_path) if relative_path != '.' else output_dir
            mp3_filepath = os.path.join(final_output_dir, mp3_filename)
            os.makedirs(final_output_dir, exist_ok=True)

            if os.path.exists(mp3_filepath):
                logging.debug(f"SKIP: MP3 '{mp3_filename}' already exists.")
                counters['skipped'] += 1
                continue

            logging.info(f"CONVERTING: '{filename}' -> '{mp3_filepath}'")
            command = ["ffmpeg", "-i", video_filepath, "-vn", "-b:a", bitrate, "-loglevel", "error", "-y", mp3_filepath]
            subprocess.run(command, check=True, capture_output=True, text=True)
            counters['converted'] += 1
            logging.info(f"SUCCESS: Converted '{filename}'.")
            
        except subprocess.CalledProcessError as e:
            logging.error(f"FAILURE: Failed to convert '{video_filepath}'.")
            logging.error(f"  FFmpeg Return Code: {e.returncode}")
            logging.error(f"  FFmpeg Error Output: {e.stderr.strip()}")
            counters['failed'] += 1
            if os.path.exists(mp3_filepath):
                os.remove(mp3_filepath)
                logging.warning(f"  CLEANUP: Removed incomplete file '{mp3_filepath}'.")
        except Exception as e:
            logging.error(f"UNEXPECTED ERROR while processing '{video_filepath}': {e}")
            counters['failed'] += 1

    logging.info("--- Conversion process finished ---")
    logging.info(f"Summary: Found={counters['found']}, Converted={counters['converted']}, Skipped={counters['skipped']}, Failed={counters['failed']}")


# === main() 函数保持不变，它负责解析参数并将它们传递给上面的函数 ===
def main():
    parser = argparse.ArgumentParser(
        description="A robust tool to batch convert video files to MP3, with JSON config support.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-c", "--config", help="Path to a JSON configuration file.")
    parser.add_argument("-i", "--input", help="Source video directory.")
    parser.add_argument("-o", "--output", help="Destination MP3 directory.")
    parser.add_argument("-r", "--recursive", action='store_true', default=None, help="Recursively search for videos.")
    parser.add_argument("-b", "--bitrate", help="Audio bitrate (e.g., '192k').")
    parser.add_argument("-l", "--logfile", help="Path to a log file.")
    parser.add_argument(
        "--no-append-extension",
        dest='append_extension',
        action='store_false',
        help="Do NOT append the original video extension to the MP3 filename."
    )
    parser.set_defaults(append_extension=True)
    args = parser.parse_args()
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error reading or parsing config file '{args.config}': {e}")
            sys.exit(1)
    final_config = {
        'input': args.input or config.get('input_directory'),
        'output': args.output or config.get('output_directory'),
        'bitrate': args.bitrate or config.get('bitrate', '192k'),
        'logfile': args.logfile or config.get('log_file'),
        'recursive': args.recursive if args.recursive is not None else config.get('recursive_search', False),
        'append_extension': args.append_extension if args.append_extension is False else config.get('append_source_extension', True)
    }
    setup_logging(final_config['logfile'])
    if not final_config['input'] or not final_config['output']:
        logging.critical("Error: Input and Output directories are mandatory.")
        sys.exit(1)
    if not os.path.isdir(final_config['input']):
        logging.critical(f"Input directory not found: {final_config['input']}")
        sys.exit(1)
    try:
        convert_videos_to_mp3(
            source_dir=final_config['input'],
            output_dir=final_config['output'],
            recursive=final_config['recursive'],
            bitrate=final_config['bitrate'],
            append_extension=final_config['append_extension']
        )
    except Exception as e:
        logging.critical(f"A top-level unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
