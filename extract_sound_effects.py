import json
import os
import time
from pathlib import Path
from openai import OpenAI
from tqdm import tqdm

# Configuration
ENHANCED_SCRIPT_JSON = "enhanced_script.json"
OUTPUT_DIR = "sound_effects_catalog"
NORMALIZED_EFFECTS_FILE = "normalized_sound_effects.json"

# Initialize OpenAI client
client = OpenAI()

def normalize_sound_effects_with_llm(effect_descriptions):
    """Use OpenAI to normalize sound effect descriptions"""
    try:
        # Group similar sound effects to reduce API calls
        unique_effects = list(set(effect_descriptions))
        
        # Batch effects to minimize API calls (up to 20 at a time)
        normalized_effects = {}
        
        for i in range(0, len(unique_effects), 20):
            batch = unique_effects[i:i+20]
            
            # Prepare the descriptions as a bulleted list
            effect_list = "\n".join([f"- {effect}" for effect in batch])
            
            response = client.responses.create(
                model="gpt-4o",
                input=[
                    {"role": "system", "content": "You're a sound design expert helping normalize sound effect descriptions for searching in professional sound libraries."},
                    {"role": "user", "content": f"Please normalize these sound effect descriptions into standard search terms that would work well in a sound effect library. For each term, provide a normalized version that's concise but specific enough to find good matches. Here are the descriptions:\n\n{effect_list}"}
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "sound_effect_normalization",
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "normalized_effects": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "original": {
                                                "type": "string",
                                                "description": "The original sound effect description"
                                            },
                                            "normalized": {
                                                "type": "string",
                                                "description": "The normalized search term for sound libraries"
                                            },
                                            "category": {
                                                "type": "string",
                                                "description": "General category of the sound (ambient, action, technology, body, transition, etc.)"
                                            },
                                            "description": {
                                                "type": "string",
                                                "description": "Brief description of what to look for in a sound library"
                                            },
                                            "alternative_search_terms": {
                                                "type": "array",
                                                "items": {
                                                    "type": "string"
                                                },
                                                "description": "Alternative search terms that might yield good results"
                                            }
                                        },
                                        "required": ["original", "normalized", "category", "description", "alternative_search_terms"]
                                    }
                                }
                            },
                            "required": ["normalized_effects"]
                        },
                        "strict": True
                    }
                }
            )
            
            try:
                normalization_data = json.loads(response.output_text)
                for item in normalization_data["normalized_effects"]:
                    normalized_effects[item["original"]] = {
                        "normalized": item["normalized"],
                        "category": item["category"],
                        "description": item["description"],
                        "alternative_search_terms": item["alternative_search_terms"]
                    }
            except Exception as e:
                print(f"Error parsing LLM response: {str(e)}")
                
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)
        
        return normalized_effects
    
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return {}
    
    
def extract_and_normalize_sound_effects():
    """Extract sound effects from the enhanced script and normalize them"""
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Read the enhanced script JSON
    try:
        with open(ENHANCED_SCRIPT_JSON, 'r', encoding='utf-8') as f:
            script_data = json.load(f)
    except Exception as e:
        print(f"Error reading enhanced script JSON: {str(e)}")
        return
    
    # Extract all sound effects
    all_effects = []
    effect_to_lines = {}
    
    for i, line in enumerate(script_data["lines"]):
        if "sound_effects" in line and line["sound_effects"]:
            for effect in line["sound_effects"]:
                all_effects.append(effect)
                if effect not in effect_to_lines:
                    effect_to_lines[effect] = []
                effect_to_lines[effect].append(i)
    
    print(f"Found {len(all_effects)} sound effect references across {len(effect_to_lines)} unique descriptions")
    
    # Normalize the sound effects using OpenAI
    print("Normalizing sound effect descriptions using language model...")
    normalized_effects = normalize_sound_effects_with_llm(list(effect_to_lines.keys()))
    
    # Create a full catalog with scene context
    catalog = []
    
    for original_effect, effect_info in normalized_effects.items():
        line_indices = effect_to_lines[original_effect]
        
        # Get context from each line where this effect is used
        contexts = []
        for idx in line_indices:
            if idx < len(script_data["lines"]):
                line = script_data["lines"][idx]
                
                # Get surrounding lines for context
                start_idx = max(0, idx - 2)
                end_idx = min(len(script_data["lines"]), idx + 3)
                context_lines = [script_data["lines"][i]["original_text"] for i in range(start_idx, end_idx)]
                
                contexts.append({
                    "line_index": idx,
                    "line_text": line["original_text"],
                    "context": context_lines,
                    "emotion": line.get("emotion", "neutral"),
                    "intensity": line.get("intensity", 5)
                })
        
        # Add to catalog
        catalog_entry = {
            "original_description": original_effect,
            "normalized": effect_info["normalized"],
            "category": effect_info["category"],
            "description": effect_info["description"],
            "alternative_search_terms": effect_info["alternative_search_terms"],
            "occurrences": len(line_indices),
            "line_indices": line_indices,
            "contexts": contexts
        }
        
        catalog.append(catalog_entry)
    
    # Sort by category and then by number of occurrences
    catalog.sort(key=lambda x: (x["category"], -x["occurrences"]))
    
    # Save the normalized effects
    with open(os.path.join(OUTPUT_DIR, NORMALIZED_EFFECTS_FILE), 'w', encoding='utf-8') as f:
        json.dump({
            "total_unique_effects": len(catalog),
            "total_effect_references": len(all_effects),
            "catalog": catalog
        }, f, indent=2)
    
    # Create a human-readable catalog
    create_human_readable_catalog(catalog)
    
    return catalog

def create_human_readable_catalog(catalog):
    """Create a human-readable catalog of sound effects"""
    with open(os.path.join(OUTPUT_DIR, "sound_effects_catalog.md"), 'w', encoding='utf-8') as f:
        f.write("# Sound Effects Catalog\n\n")
        f.write(f"Total unique sound effects: {len(catalog)}\n\n")
        
        # Group by category
        categories = {}
        for entry in catalog:
            category = entry["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(entry)
        
        # Write each category
        for category, entries in categories.items():
            f.write(f"## {category.title()} Sounds\n\n")
            
            # Write each sound effect
            for entry in entries:
                f.write(f"### {entry['normalized']}\n\n")
                f.write(f"**Original Description:** {entry['original_description']}\n\n")
                f.write(f"**Description:** {entry['description']}\n\n")
                f.write(f"**Alternative Search Terms:** {', '.join(entry['alternative_search_terms'])}\n\n")
                f.write(f"**Occurrences:** {entry['occurrences']}\n\n")
                
                # Write a few example contexts
                f.write("**Example Contexts:**\n\n")
                for i, context in enumerate(entry["contexts"][:3]):  # Show max 3 examples
                    f.write(f"Context {i+1}:\n")
                    f.write("```\n")
                    for line in context["context"]:
                        if line == context["line_text"]:
                            f.write(f"> {line}\n")
                        else:
                            f.write(f"{line}\n")
                    f.write("```\n\n")
                
                f.write("---\n\n")
    
    print(f"Created human-readable catalog: {os.path.join(OUTPUT_DIR, 'sound_effects_catalog.md')}")
    
    # Also create a CSV for easier importing
    with open(os.path.join(OUTPUT_DIR, "sound_effects_list.csv"), 'w', encoding='utf-8') as f:
        f.write("Category,Normalized Name,Description,Alternative Search Terms,Occurrences\n")
        for entry in catalog:
            alt_terms = "|".join(entry["alternative_search_terms"])
            f.write(f"\"{entry['category']}\",\"{entry['normalized']}\",\"{entry['description']}\",\"{alt_terms}\",{entry['occurrences']}\n")
    
    print(f"Created CSV list: {os.path.join(OUTPUT_DIR, 'sound_effects_list.csv')}")


    



if __name__ == "__main__":
    print("Extracting and normalizing sound effects...")
    catalog = extract_and_normalize_sound_effects()
    
    if catalog:
        print(f"Created sound effects catalog with {len(catalog)} unique effects")

    else:
        print("Failed to create sound effects catalog")
    
    print("Done!")
    
    