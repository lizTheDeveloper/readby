import json
import os
import shutil
from pathlib import Path
from pydub import AudioSegment

# Configuration
SOUND_EFFECTS_DIR = "downloaded_sound_effects"
NORMALIZED_EFFECTS_FILE = "sound_effects_catalog/normalized_sound_effects.json"
ENHANCED_SCRIPT_JSON = "enhanced_script.json"
MAPPING_FILE = "sound_effect_mapping.json"

def list_missing_sounds():
    """List all normalized sound effects that haven't been downloaded yet"""
    # Load the normalized effects
    with open(NORMALIZED_EFFECTS_FILE, 'r', encoding='utf-8') as f:
        catalog_data = json.load(f)
    
    # Check which sounds exist
    os.makedirs(SOUND_EFFECTS_DIR, exist_ok=True)
    existing_files = os.listdir(SOUND_EFFECTS_DIR)
    
    # List missing sounds
    missing_sounds = []
    for entry in catalog_data["catalog"]:
        normalized = entry["normalized"]
        safe_name = normalized.replace(" ", "_").lower()
        
        found = False
        for ext in [".mp3", ".wav", ".ogg"]:
            if f"{safe_name}{ext}" in existing_files:
                found = True
                break
        
        if not found:
            missing_sounds.append({
                "normalized": normalized,
                "category": entry["category"],
                "description": entry["description"],
                "alternative_search_terms": entry["alternative_search_terms"],
                "occurrences": entry["occurrences"]
            })
    
    # Sort by occurrences (most used first)
    missing_sounds.sort(key=lambda x: -x["occurrences"])
    
    # Print missing sounds
    if missing_sounds:
        print(f"\\nMissing {len(missing_sounds)} sound effects:")
        for i, sound in enumerate(missing_sounds):
            print(f"{i+1}. {sound['normalized']} ({sound['category']}) - Used {sound['occurrences']} times")
            print(f"   Description: {sound['description']}")
            print(f"   Alternative search terms: {', '.join(sound['alternative_search_terms'])}")
            print()
    else:
        print("All sound effects have been downloaded!")
    
    return missing_sounds

def update_sound_mapping():
    """Update the sound effect mapping based on downloaded files"""
    # Load the normalized effects
    with open(NORMALIZED_EFFECTS_FILE, 'r', encoding='utf-8') as f:
        catalog_data = json.load(f)
    
    # Check which sounds exist
    os.makedirs(SOUND_EFFECTS_DIR, exist_ok=True)
    existing_files = os.listdir(SOUND_EFFECTS_DIR)
    
    # Create mapping
    mapping = {}
    
    for entry in catalog_data["catalog"]:
        normalized = entry["normalized"]
        original = entry["original_description"]
        safe_name = normalized.replace(" ", "_").lower()
        
        # Check for files with common audio extensions
        for ext in [".mp3", ".wav", ".ogg"]:
            filename = f"{safe_name}{ext}"
            if filename in existing_files:
                mapping[original] = os.path.join(SOUND_EFFECTS_DIR, filename)
                break
    
    # Save the mapping
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"Updated sound mapping file: {MAPPING_FILE}")
    print(f"Mapped {len(mapping)} sound effects")
    
    return mapping

def update_script_with_sounds():
    """Update the enhanced script with sound effect file paths"""
    # Load the mapping
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    # Load the enhanced script
    with open(ENHANCED_SCRIPT_JSON, 'r', encoding='utf-8') as f:
        script_data = json.load(f)
    
    # Update the script with sound effect file paths
    for i, line in enumerate(script_data["lines"]):
        if "sound_effects" in line and line["sound_effects"]:
            # Initialize sound_effect_files if it doesn't exist
            if "sound_effect_files" not in line:
                line["sound_effect_files"] = []
            else:
                line["sound_effect_files"] = []  # Reset to avoid duplicates
            
            # Add the sound effect files
            for effect in line["sound_effects"]:
                if effect in mapping:
                    line["sound_effect_files"].append(mapping[effect])
    
    # Save the updated script
    with open("enhanced_script_with_sounds.json", 'w', encoding='utf-8') as f:
        json.dump(script_data, f, indent=2)
    
    print("Enhanced script updated with sound effect file paths")

def main():
    """Main function"""
    print("\\n==== Sound Effect Manager ====\\n")
    print("1. List missing sound effects")
    print("2. Update sound mapping")
    print("3. Update script with sounds")
    print("4. All of the above")
    print("q. Quit")
    
    choice = input("\\nEnter your choice: ")
    
    if choice == "1":
        list_missing_sounds()
    elif choice == "2":
        update_sound_mapping()
    elif choice == "3":
        update_script_with_sounds()
    elif choice == "4":
        list_missing_sounds()
        update_sound_mapping()
        update_script_with_sounds()
    elif choice.lower() == "q":
        print("Goodbye!")
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()