from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment
from pydub.playback import play
import os
import json
import time
import sys

class StoryGenerator:
    def __init__(self, json_file, output_dir="audio_output"):
        """Initialize the story generator with the script file and output directory"""
        self.output_dir = output_dir
        self.json_file = json_file
        os.makedirs(output_dir, exist_ok=True)
        
        # Load the script data
        with open(json_file, "r", encoding="utf-8") as f:
            self.script_data = json.load(f)
        
        # Initialize OpenAI client
        self.client = OpenAI()
        
        # Verify file paths and update script
        self.validate_audio_files()
        
    def validate_audio_files(self):
        """Check if audio files exist and update the script accordingly"""
        print("Validating existing audio files...")
        lines_updated = False
        
        # Ensure every line has an audio_file field
        for i, line in enumerate(self.script_data["lines"]):
            expected_file = f"{self.output_dir}/line{i+1}.mp3"
            
            # Add or update audio_file path
            if "audio_file" in line:
                # If file doesn't exist, remove the path
                if not os.path.exists(line["audio_file"]):
                    print(f"File not found: {line['audio_file']}, marking for regeneration")
                    line.pop("audio_file", None)
                    line["needs_regeneration"] = True
                    lines_updated = True
            else:
                # Check if the expected file exists
                if os.path.exists(expected_file):
                    line["audio_file"] = expected_file
                    line["needs_regeneration"] = False
                    lines_updated = True
                else:
                    line["needs_regeneration"] = True
                    lines_updated = True
        
        # Save updates to script file
        if lines_updated:
            self.save_script()
        
        # Count how many lines need generation
        lines_to_generate = sum(1 for line in self.script_data["lines"] if line.get("needs_regeneration", True))
        print(f"{lines_to_generate} out of {len(self.script_data['lines'])} lines need generation")
        self.last_generated_line = len(self.script_data["lines"]) - lines_to_generate
        print(f"Last generated line: {self.last_generated_line + 1}")

    def save_script(self):
        """Save the current script data back to the JSON file"""
        with open(self.json_file, "w", encoding="utf-8") as f:
            json.dump(self.script_data, f, indent=2)
        print(f"Updated script saved to {self.json_file}")
    
    def generate_audio_for_line(self, line_index):
        """Generate audio for a specific line in the script"""
        if line_index >= len(self.script_data["lines"]):
            print("Line index out of range")
            return False
            
        line = self.script_data["lines"][line_index]
        temp_file = f"{self.output_dir}/line{line_index+1}.mp3"
        
        print(f"\nGenerating audio for line {line_index+1}...")
        print(f"Text: {line['original_text']}")
        print(f"Voice instructions: {line['voice_instructions']}")
        
        try:
            # Generate speech using OpenAI's TTS
            with self.client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="fable",
                input=line["original_text"],
                instructions=line["voice_instructions"],
            ) as response:
                response.stream_to_file(temp_file)
            
            print(f"Generated: {temp_file}")
            
            # Update the script data
            line["audio_file"] = temp_file
            line["needs_regeneration"] = False
            self.save_script()
            
            return True
        except Exception as e:
            print(f"Error generating audio: {str(e)}")
            return False
    
    def play_audio(self, line_index):
        """Play the audio for a specific line"""
        line = self.script_data["lines"][line_index]
        
        if "audio_file" in line and os.path.exists(line["audio_file"]):
            print(f"Playing line {line_index+1}...")
            audio = AudioSegment.from_mp3(line["audio_file"])
            play(audio)
            return True
        else:
            print(f"Audio file for line {line_index+1} doesn't exist")
            return False
    
    def mark_for_regeneration(self, line_index, new_instructions=None):
        """Mark a line for regeneration, optionally with new voice instructions"""
        if line_index >= len(self.script_data["lines"]):
            print("Line index out of range")
            return False
            
        line = self.script_data["lines"][line_index]
        line["needs_regeneration"] = True
        
        if new_instructions:
            # Update the voice instructions for this line
            line["voice_instructions"] = new_instructions
            print(f"Updated voice instructions for line {line_index+1}")
        
        # If file exists, optionally delete it
        if "audio_file" in line and os.path.exists(line["audio_file"]):
            choice = input(f"Delete existing audio file {line['audio_file']}? (y/n): ").lower()
            if choice == 'y':
                os.remove(line["audio_file"])
                line.pop("audio_file", None)
        
        self.save_script()
        return True
    
    def interactive_generation(self, start_line=0, end_line=None):
        """Generate audio interactively, with feedback after each line"""
        if end_line is None:
            end_line = len(self.script_data["lines"]) - 1
            
        for line_index in range(start_line, end_line + 1):
            line = self.script_data["lines"][line_index]
            
            # Skip if this line already has audio and doesn't need regeneration
            if "audio_file" in line and os.path.exists(line["audio_file"]) and not line.get("needs_regeneration", False):
                print(f"\nLine {line_index+1} already has audio. Play it? (y/n/r): ", end="")
                choice = input().lower()
                
                if choice == 'y':
                    self.play_audio(line_index)
                    ## give the user a chance to regenerate
                    
                elif choice == 'r':
                    line["needs_regeneration"] = True
                
                if not line.get("needs_regeneration", False):
                    continue
            
            # Generate audio for this line
            success = self.generate_audio_for_line(line_index)
            if not success:
                print(f"Failed to generate audio for line {line_index+1}")
                continue
            
            # Play the generated audio
            self.play_audio(line_index)
            
            # Get feedback
            while True:
                print("\nOptions:")
                print("  [g]ood - Accept and continue")
                print("  [r]egenerate - Regenerate with same instructions")
                print("  [m]odify - Modify voice instructions and regenerate")
                print("  [s]kip - Continue without accepting")
                print("  [q]uit - Stop generation")
                choice = input("Your choice: ").lower()
                
                if choice == 'g':
                    # Accept and continue
                    break
                elif choice == 'r':
                    # Regenerate with same instructions
                    line["needs_regeneration"] = True
                    self.save_script()
                    success = self.generate_audio_for_line(line_index)
                    if success:
                        self.play_audio(line_index)
                    else:
                        print("Failed to regenerate audio")
                elif choice == 'm':
                    # Modify instructions and regenerate
                    print(f"Current instructions: {line['voice_instructions']}")
                    new_instructions = input("Enter new voice instructions: ")
                    line["voice_instructions"] = new_instructions
                    line["needs_regeneration"] = True
                    self.save_script()
                    success = self.generate_audio_for_line(line_index)
                    if success:
                        self.play_audio(line_index)
                    else:
                        print("Failed to regenerate audio")
                elif choice == 's':
                    # Skip without accepting
                    line["needs_regeneration"] = True
                    self.save_script()
                    break
                elif choice == 'q':
                    # Quit generation
                    return False
        
        return True
    
    def batch_regeneration(self):
        """Generate all lines marked for regeneration without interaction"""
        for line_index, line in enumerate(self.script_data["lines"]):
            if line.get("needs_regeneration", True):
                print(f"Generating line {line_index+1}...")
                self.generate_audio_for_line(line_index)
        
        print("Batch generation complete")
    
    def batch_generation(self):
        """Generate all ungenerated lines in the script without interaction"""
        for line_index, line in enumerate(self.script_data["lines"]):
            if not line.get("audio_file"):
                print(f"Generating line {line_index+1}...")
                self.generate_audio_for_line(line_index)
        print("Batch generation complete")
    
    def combine_audio_files(self):
        """Combine all generated audio files into a complete narrative"""
        print("\nCombining audio files...")
        combined = AudioSegment.empty()
        missing_files = []
        
        # Process each line
        for line_index, line in enumerate(self.script_data["lines"]):
            if "audio_file" in line and os.path.exists(line["audio_file"]):
                # Add the line audio
                audio_segment = AudioSegment.from_mp3(line["audio_file"])
                combined += audio_segment
                
                # Add pause based on context (without sound effects)
                pause_duration = int(line["pause_after"] * 1000)
                silence = AudioSegment.silent(duration=pause_duration)
                combined += silence
            else:
                print(f"Warning: Missing audio for line {line_index+1}")
                missing_files.append(line_index+1)
        
        if missing_files:
            print(f"Warning: {len(missing_files)} lines are missing audio: {missing_files}")
            choice = input("Continue with missing files? (y/n): ").lower()
            if choice != 'y':
                return None
        
        # Export the final combined audio
        final_output = f"{self.output_dir}/complete_story.mp3"
        combined.export(final_output, format="mp3")
        print(f"Exported complete story: {final_output}")
        return final_output
    
    def play_combined(self):
        """Play the combined story audio"""
        final_output = f"{self.output_dir}/complete_story.mp3"
        if os.path.exists(final_output):
            print(f"Playing complete story...")
            audio = AudioSegment.from_mp3(final_output)
            play(audio)
            return True
        else:
            print("Combined audio file doesn't exist yet")
            final_output = self.combine_audio_files()
            if final_output:
                return self.play_combined()
            return False

def main():
    """Main function to run the story generator"""
    # Check command-line arguments
    if len(sys.argv) < 2:
        print("Usage: python script.py <json_file> [output_dir]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "audio_output"
    
    # Create generator
    generator = StoryGenerator(json_file, output_dir)
    
    # Interactive menu
    while True:
        print("\n=== Story Audio Generator ===")
        print("1. Interactive generation (with feedback)")
        print("2. Generate specific section interactively")
        print("3. Batch generate all ungenerated lines")
        print("4. Mark specific line for regeneration")
        print("5. Play specific line")
        print("6. Combine all audio files")
        print("7. Play complete story")
        print("8. Validate audio files")
        print("9. Exit")
        
        choice = input("Enter your choice (1-9): ")
        
        if choice == '1':
            generator.interactive_generation()
            
        elif choice == '2':
            start = input("Enter start line (1-based): ")
            end = input("Enter end line (1-based): ")
            if not start.isdigit():
                ## start on the last generated line
                start = generator.last_generated_line
            if not end.isdigit():
                ## end on the last line
                end = len(generator.script_data["lines"]) - 1
            generator.interactive_generation(int(start), int(end))
            
        elif choice == '3':
            generator.batch_generation()
            
        elif choice == '4':
            line = int(input("Enter line to mark for regeneration (1-based): ")) - 1
            modify = input("Modify voice instructions? (y/n): ").lower() == 'y'
            
            if modify:
                instructions = input("Enter new voice instructions: ")
                generator.mark_for_regeneration(line, instructions)
            else:
                generator.mark_for_regeneration(line)
            
        elif choice == '5':
            line = int(input("Enter line to play (1-based): ")) - 1
            generator.play_audio(line)
            
        elif choice == '6':
            generator.combine_audio_files()
            
        elif choice == '7':
            generator.play_combined()
            
        elif choice == '8':
            generator.validate_audio_files()
            
        elif choice == '9':
            print("Exiting...")
            break
            
        else:
            print("Invalid choice, please try again")

if __name__ == "__main__":
    main()