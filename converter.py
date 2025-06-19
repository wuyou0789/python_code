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

config.json:
{
  "input_directory": "/path/to/your/videos",
  "output_directory": "/path/to/save/music",
  "recursive_search": true,
  "bitrate": "192k",
  "log_file": "/var/log/video_conversion.log",
  "append_source_extension": true
}

input_directory (字符串, 必填):
说明：包含源视频文件的目录的绝对路径。
例子："/mnt/nas/videos_to_convert"
output_directory (字符串, 必填):
说明：用于保存转换后 MP3 文件的目标目录的绝对路径。脚本会自动创建此目录（如果不存在）。
例子："/mnt/nas/converted_audio"
recursive_search (布尔值, 可选, 默认 false):
说明：如果设置为 true，脚本将递归搜索 input_directory 下的所有子目录来查找视频文件。如果为 false，则只处理 input_directory 根目录下的文件。
例子：true
bitrate (字符串, 可选, 默认 "192k"):
说明：输出 MP3 文件的音频比特率。值越高，音质越好，文件也越大。
例子："128k", "192k", "320k"
log_file (字符串, 可选, 默认 null 或不提供):
说明：指定一个日志文件的绝对路径。如果提供此项，所有运行日志都将追加到此文件中；否则，日志将直接输出到控制台（标准输出）。
例子："/home/user/logs/conversion.log"
append_source_extension (布尔值, 可选, 默认 true):
说明：决定是否将原始视频的扩展名附加到输出的 MP3 文件名中。
设置为 true (默认)：video.mp4 → video_mp4.mp3。这是更安全的选项，可以避免因不同格式的同名视频（如 file.mp4 和 file.mkv）导致的输出文件冲突。
设置为 false：video.mp4 → video.mp3。文件名更简洁，但如果存在同名不同格式的源文件，后面的转换会覆盖前面的结果。
例子：false

================================================================================
"""
import os
import sys
import json
import argparse
import subprocess
import logging
import re # <<< 新增：导入正则表达式模块

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
