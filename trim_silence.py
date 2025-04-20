#!/usr/bin/env python3

import os
import argparse
import numpy as np
from pydub import AudioSegment
import soundfile as sf
import glob

def detect_and_trim_silence(file_path, output_dir, silence_threshold_db=-50, min_silence_duration=1000):
    """
    Analyzes an audio file, detects extended silences, and trims the file at the first second of silence.
    
    Args:
        file_path: Path to the audio file
        output_dir: Directory to save the trimmed file
        silence_threshold_db: Threshold in dB to consider as silence (default: -50 dB)
        min_silence_duration: Minimum duration of silence in milliseconds (default: 1000 ms = 1 second)
    
    Returns:
        Path to the trimmed file or None if no silence was found
    """
    try:
        # Load the audio file
        print(f"Processing {file_path}...")
        audio = AudioSegment.from_file(file_path)
        
        # Convert silence threshold from dB to amplitude ratio
        silence_threshold = audio.dBFS + silence_threshold_db
        
        # Get chunks that are silent
        silence_starts = []
        
        # Check for silence in chunks of 10ms
        chunk_size = 10
        
        for i in range(0, len(audio) - chunk_size, chunk_size):
            chunk = audio[i:i+chunk_size]
            if chunk.dBFS < silence_threshold:
                silence_starts.append(i)
            elif len(silence_starts) > 0:
                # If we found silence but now there's sound, reset
                silence_starts = []
                
            # Check if we have accumulated enough silent chunks to meet min_silence_duration
            if len(silence_starts) * chunk_size >= min_silence_duration:
                # We found our first second of silence
                trim_point = silence_starts[0]
                print(f"Found silence at {trim_point/1000:.2f} seconds")
                
                # Trim the audio
                trimmed_audio = audio[:trim_point]
                
                # Create output filename
                filename = os.path.basename(file_path)
                base_name, ext = os.path.splitext(filename)
                output_path = os.path.join(output_dir, f"{base_name}{ext}")
                
                # Export the trimmed audio
                trimmed_audio.export(output_path, format=ext.replace('.', ''))
                print(f"Trimmed file saved to {output_path}")
                
                return output_path
                
        # If we get here, no extended silence was found
        print(f"No extended silence found in {file_path}")
        return None
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Trim audio files at the first detection of extended silence.')
    parser.add_argument('input_dir', type=str, help='Directory containing audio files to process')
    parser.add_argument('--output_dir', type=str, help='Directory to save trimmed files (defaults to input_dir/trimmed)')
    parser.add_argument('--silence_threshold', type=float, default=-50, help='Silence threshold in dB (default: -50)')
    parser.add_argument('--silence_duration', type=float, default=1.0, help='Minimum silence duration in seconds (default: 1.0)')
    parser.add_argument('--extensions', type=str, default='.mp3,.wav,.flac,.ogg,.m4a', help='Comma-separated list of audio file extensions to process')
    
    args = parser.parse_args()
    
    # Ensure input directory exists
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory {args.input_dir} does not exist")
        return 1
    
    # Set up output directory
    output_dir = args.output_dir if args.output_dir else os.path.join(args.input_dir, 'trimmed')
    os.makedirs(output_dir, exist_ok=True)
    
    # Get list of audio files
    extensions = args.extensions.split(',')
    audio_files = []
    for ext in extensions:
        audio_files.extend(glob.glob(os.path.join(args.input_dir, f"*{ext}")))
    
    if not audio_files:
        print(f"No audio files with extensions {args.extensions} found in {args.input_dir}")
        return 1
    
    print(f"Found {len(audio_files)} audio files to process")
    
    # Process each file
    processed_count = 0
    trimmed_count = 0
    
    for file_path in audio_files:
        processed_count += 1
        result = detect_and_trim_silence(
            file_path, 
            output_dir, 
            silence_threshold_db=args.silence_threshold,
            min_silence_duration=int(args.silence_duration * 1000)
        )
        
        if result:
            trimmed_count += 1
    
    print(f"\nProcessing complete. Processed {processed_count} files, trimmed {trimmed_count} files.")
    print(f"Trimmed files saved to {output_dir}")
    
    return 0

if __name__ == "__main__":
    exit(main())