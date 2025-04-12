from pathlib import Path
from openai import OpenAI
import tiktoken
import json
import os
import time

# Initialize OpenAI client
client = OpenAI()

def split_text_into_chunks(input_file="input.txt", max_tokens=1900):
    """Split the input file into manageable chunks for processing"""
    try:
        # Read the input file
        with open(input_file, "r", encoding="utf-8") as f:
            text = f.read()
        
        # Initialize the tokenizer
        encoding = tiktoken.get_encoding("cl100k_base")
        
        # Split into lines
        lines = [line for line in text.splitlines() if line.strip()]
        
        # Get token count for each line
        line_tokens = [len(encoding.encode(line)) for line in lines]
        
        return lines, line_tokens
    except Exception as e:
        print(f"Error splitting text: {str(e)}")
        return [], []

def analyze_line_with_llm(line, context_lines, line_index, total_lines, characters_seen=[]):
    """Use OpenAI to analyze the emotional context and suggest sound effects"""
    # Compile the context window (5 lines before and after if available)
    start_idx = max(0, line_index - 5)
    end_idx = min(total_lines, line_index + 6)
    context = "\n".join(context_lines[start_idx:end_idx])
    
    # Highlight the current line in the context
    context_with_highlight = context.replace(line, f"[CURRENT LINE]: {line}")
    
    try:
        response = client.responses.create(
            model="gpt-4o",
            input=[
                {"role": "system", "content": "You are a script analysis assistant specializing in dramatic readings. Analyze the emotional context of the provided line within its surrounding context. Identify dialogue, characters, emotions, and suggest appropriate voice modulation and sound effects."},
                {"role": "user", "content": f"Here's a segment from a story, with the current line marked as [CURRENT LINE]:\n\n{context_with_highlight}\n\nAnalyze the current line for: dialogue detection, character identification (who is speaking?), emotional content, appropriate pause length after this line, and sound effect suggestions. We've seen these characters so far: {', '.join(characters_seen)}. If there is no character, Narrator is the character. Provide a detailed analysis in JSON format."}
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "line_analysis",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "is_dialogue": {
                                "type": "string",
                                "description": "Whether this line contains dialogue, true or false"
                            },
                            "character": {
                                "type": "string",
                                "description": "The character speaking, if identified"
                            },
                            "emotion": {
                                "type": "string",
                                "description": "The primary emotion in this line (fear, anger, sadness, joy, tension, excitement, mystery, surprise, calm, neutral, etc.)"
                            },
                            "intensity": {
                                "type": "string",
                                "description": "Emotional intensity on a scale from 1-10"
                            },
                            "pause_after": {
                                "type": "string",
                                "description": "Recommended pause after this line in seconds (0.5-3.0)"
                            },
                            "voice_instructions": {
                                "type": "string",
                                "description": "Detailed instructions for voice modulation"
                            },
                            "is_scene_transition": {
                                "type": "string",
                                "description": "Whether this line indicates a scene transition"
                            },
                            "is_action": {
                                "type": "string",
                                "description": "Whether this line describes action"
                            },
                            "sound_effects": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Suggested sound effects that would enhance this line"
                            }
                        },
                        "required": ["is_dialogue", "emotion", "intensity", "pause_after", "voice_instructions", "sound_effects", "is_action", "is_scene_transition", "character"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        )
        
        analysis = json.loads(response.output_text)
        return analysis
    
    except Exception as e:
        print(f"Error analyzing line with LLM: {str(e)}")
        # Return default values in case of error
        return {
            "is_dialogue": False,
            "character": None,
            "emotion": "neutral",
            "intensity": 5,
            "pause_after": 1.0,
            "voice_instructions": "Read in a natural, clear voice.",
            "is_scene_transition": False,
            "is_action": False,
            "sound_effects": []
        }

def analyze_script(input_file="input.txt", output_file="enhanced_script.txt", json_output="enhanced_script.json"):
    """Analyze the input script and create an enhanced version with emotional and sound cues"""
    print(f"Reading and analyzing script from {input_file}...")
    
    # Get the lines and token counts
    lines, line_tokens = split_text_into_chunks(input_file)
    if not lines:
        return "Failed to read input file"
    
    # Create a directory for progress tracking
    os.makedirs("analysis_progress", exist_ok=True)
    progress_file = "analysis_progress/progress.json"
    
    # Check if we're resuming an incomplete analysis
    analyses = []
    start_index = 0
    
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                progress_data = json.load(f)
                analyses = progress_data.get("analyses", [])
                start_index = len(analyses)
                print(f"Resuming analysis from line {start_index + 1} of {len(lines)}")
        except:
            print("Could not read progress file. Starting from the beginning.")
    characters_seen = set()
    # Process each line
    for i in range(start_index, len(lines)):
        print(f"Analyzing line {i+1} of {len(lines)}: {lines[i][:50]}...")
        analysis = analyze_line_with_llm(lines[i], lines, i, len(lines), characters_seen)
        
        # Store the original line and token count with the analysis
        analysis["original_text"] = lines[i]
        analysis["token_count"] = line_tokens[i]
        characters_seen.add(analysis["character"])
        
        # Add to our analyses list
        analyses.append(analysis)
        
        # Save progress after each analysis
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump({"analyses": analyses}, f, indent=2)
        
        # Add a small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Create the enhanced script file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=== ENHANCED SCRIPT WITH EMOTIONAL AND SOUND CUES ===\n\n")
        
        for i, analysis in enumerate(analyses):
            f.write(f"[Line {i+1}]\n")
            f.write(f"TEXT: {analysis['original_text']}\n")
            
            if analysis['is_dialogue']:
                f.write(f"DIALOGUE: Yes")
                if analysis['character']:
                    f.write(f" (Character: {analysis['character']})")
                f.write("\n")
            
            f.write(f"EMOTION: {analysis['emotion']} (Intensity: {analysis['intensity']})\n")
            f.write(f"VOICE: {analysis['voice_instructions']}\n")
            
            if analysis['sound_effects']:
                f.write(f"SOUND EFFECTS: {', '.join(analysis['sound_effects'])}\n")
            
            f.write(f"PAUSE AFTER: {analysis['pause_after']} seconds\n")
            f.write("\n")
    
    # Create the JSON output for programmatic use
    with open(json_output, "w", encoding="utf-8") as f:
        enhanced_script = {
            "lines": analyses,
            "total_lines": len(analyses),
            "total_tokens": sum(analysis["token_count"] for analysis in analyses)
        }
        json.dump(enhanced_script, f, indent=2)
    
    return analyses


# Main execution
if __name__ == "__main__":
    input_file = "input.txt"
    enhanced_script_file = "enhanced_script.txt"
    json_script_file = "enhanced_script.json"
    
    # Analyze the script
    analyses = analyze_script(input_file, enhanced_script_file, json_script_file)
    
    if isinstance(analyses, list):
        print(f"Enhanced script created: {enhanced_script_file}")
        print(f"Enhanced script JSON created: {json_script_file}")
        
    else:
        print(analyses)  # Print error message