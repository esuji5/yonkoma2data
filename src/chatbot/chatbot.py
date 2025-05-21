import json
import re
import os

# Global variable to store script data
SCRIPT_DATA = []

def load_script_data(filepath="src/chatbot/readme_data.json"):
    """
    Loads script data from the specified JSON file into the global SCRIPT_DATA.
    Adjusts the filepath to be relative to this script's location.
    """
    global SCRIPT_DATA
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.basename(filepath)
    absolute_filepath = os.path.join(base_dir, filename)

    try:
        with open(absolute_filepath, 'r', encoding='utf-8') as f:
            SCRIPT_DATA = json.load(f)
    except FileNotFoundError:
        # This print will be visible if run directly, but not in typical execution environment
        # print(f"Error: Data file not found at {absolute_filepath}") 
        SCRIPT_DATA = [] # Ensure SCRIPT_DATA is empty if file not found
    except json.JSONDecodeError:
        # print(f"Error: Could not decode JSON from {absolute_filepath}")
        SCRIPT_DATA = []

def find_mentioned_scripts(query, script_data):
    """
    Identifies scripts mentioned in the user's query.
    """
    mentioned_scripts = []
    query_lower = query.lower()

    if not script_data: # Handle case where SCRIPT_DATA might be empty
        return []

    for script_info in script_data:
        script_name = script_info.get("script_name", "")
        script_name_lower = script_name.lower()
        title_lower = script_info.get("title", "").lower()

        if script_name_lower and script_name_lower in query_lower:
            if script_name not in mentioned_scripts:
                mentioned_scripts.append(script_name)
            continue 

        base_script_name = script_name_lower.split('.')[0] 
        if base_script_name and base_script_name != script_name_lower and base_script_name in query_lower : # ensure base_script_name is different and present
            if script_name not in mentioned_scripts:
                mentioned_scripts.append(script_name)
            continue
            
        simplified_title_parts = []
        # Simplified heuristics - these could be expanded or made more robust
        if "pdf" in title_lower and ("renamer" in title_lower or "リネーム" in title_lower):
            simplified_title_parts.append("pdf renamer")
        if "pdf" in title_lower and ("pages" in title_lower or "ページ" in title_lower):
            simplified_title_parts.append("pdf to pages")
        if "amane_cut" in title_lower or ("amane" in title_lower and "cut" in title_lower): # "amane_cut.py" or "amane cut"
            simplified_title_parts.append("amane cut")
            simplified_title_parts.append("amane_cut.py") 
        if "mogrify" in title_lower: 
            simplified_title_parts.append("mogrify")
        if "ocr" in title_lower and ("jpg" in title_lower or "画像" in title_lower): 
            simplified_title_parts.append("jpg to ocr")
        if "pickle" in title_lower and ("serif" in title_lower or "csv" in title_lower): 
            simplified_title_parts.append("pickle to serif")
        
        found_by_title_part = False
        for part in simplified_title_parts:
            if part in query_lower:
                original_script_name_for_part = script_info.get("script_name") 
                if original_script_name_for_part not in mentioned_scripts:
                    mentioned_scripts.append(original_script_name_for_part)
                found_by_title_part = True
                break
        if found_by_title_part:
            continue
            
    return list(set(mentioned_scripts))


def identify_intent(query):
    """
    Identifies the user's intent based on keywords in the query.
    """
    query_lower = query.lower()

    if any(k in query_lower for k in ["how to run", "execute", "run", "実行方法", "実行"]):
        return "run_script"
    if any(k in query_lower for k in ["what does it do", "describe", "explain", "purpose", "detail", "details", "概要", "説明", "何をする"]):
        return "describe_script"
    if any(k in query_lower for k in ["arguments", "args", "params", "options", "parameters", "引数", "オプション", "パラメータ"]):
        return "get_arguments"
    if any(k in query_lower for k in ["requirements", "dependencies", "needs", "install", "require", "dependency", "前提", "インストール", "必要なもの"]):
        return "get_requirements"
    if any(k in query_lower for k in ["example", "usage", "show me how", "使用例", "例"]):
        return "get_examples"
    
    return None

def generate_response(mentioned_script_names, intent, all_script_data):
    """
    Generates a user-friendly response based on identified scripts and intent.
    """
    responses = []

    if not all_script_data: 
        return "I'm sorry, but I don't have any script data loaded. Please check the readme_data.json file."

    if not mentioned_script_names:
        # If no specific intent, and no script, it's a general unclear query.
        if not intent:
             return "I'm sorry, I couldn't understand your request. Could you please be more specific about a script or what you want to know?"
        # If there's an intent but no script, ask for script.
        return "I'm sorry, I couldn't identify which script you're asking about for that action. Please specify a script name."


    if not intent:
        script_list_str = ", ".join(mentioned_script_names)
        if len(mentioned_script_names) == 1:
            script_info_single = next((s for s in all_script_data if s.get("script_name") == mentioned_script_names[0]), None)
            if script_info_single:
                title_single = script_info_single.get("title", mentioned_script_names[0])
                description_single = script_info_single.get("description", "").strip()
                if description_single:
                    # Clean up description for display
                    description_single_formatted = description_single.replace("\\n", "\n  ")
                    return f"Here's a description for '{title_single}':\n  {description_single_formatted}\nWhat else would you like to know about it (e.g., how to run, arguments, requirements)?"
                else:
                    return f"No specific description found for '{title_single}'. What would you like to know about it? (e.g., how to run, arguments, requirements)"
        return f"I'm not sure what you want to know about {script_list_str}. Could you please rephrase? (e.g., 'how to run ...', 'what does ... do?', 'arguments for ...')"

    for script_name in mentioned_script_names:
        script_info = next((s for s in all_script_data if s.get("script_name") == script_name), None)

        if not script_info:
            responses.append(f"Script '{script_name}' not found in my data.")
            continue

        title = script_info.get("title", script_name)
        response_part = f"\nFor '{title}':\n"

        if intent == "describe_script":
            description = script_info.get("description", "").strip()
            if description:
                description_formatted = description.replace("\\n", "\n    ") # ensure newlines in desc are formatted
                response_part += f"  Description: {description_formatted}\n"
            else:
                response_part += "  No specific description found.\n"
        
        elif intent == "run_script":
            run_command = script_info.get("run_command", "").strip()
            if run_command:
                response_part += f"  To run it: {run_command}\n"
                if script_info.get("requirements"):
                     response_part += "  Make sure you have met all requirements before running.\n"
            else:
                response_part += "  No run command found.\n"

        elif intent == "get_arguments":
            arguments = script_info.get("arguments", [])
            if arguments and isinstance(arguments, list) and len(arguments) > 0:
                response_part += "  Arguments:\n"
                for arg_info in arguments:
                    arg_line = f"    - {arg_info.get('arg')}"
                    if arg_info.get('default'):
                        arg_line += f" (default: {arg_info.get('default')})"
                    desc = arg_info.get('description', "")
                    if desc: 
                        arg_line += f": {desc}"
                    response_part += arg_line + "\n"
            elif isinstance(arguments, str) and arguments.strip():
                 response_part += f"  Arguments information: {arguments}\n"
            else:
                response_part += "  No specific arguments listed for this script.\n"

        elif intent == "get_requirements":
            requirements = script_info.get("requirements", [])
            if requirements:
                response_part += "  Requirements:\n"
                for req in requirements:
                    response_part += f"    - {req}\n"
            else:
                response_part += "  No specific requirements listed.\n"
        
        elif intent == "get_examples":
            example_usage = script_info.get("example_usage", "").strip()
            if example_usage:
                example_usage_formatted = example_usage.replace("\\n", "\n    ")
                response_part += f"  Example Usage:\n    {example_usage_formatted}\n"
            else:
                response_part += "  No examples found.\n"
        
        else: 
            response_part += "  I'm not sure how to answer that intent.\n"
            
        responses.append(response_part)

    return "".join(responses) if responses else "I couldn't generate a response. Please try again."


# Main execution block
if __name__ == "__main__":
    load_script_data() 

    if not SCRIPT_DATA:
        print("Chatbot Error: No script data loaded. Please ensure 'readme_data.json' is in the same directory and contains valid JSON data. Exiting.")
    else:
        # --- Start of testing block ---
        test_queries = [
            "hello there",
            "what does pdf_renamer_by_isbn.py do?",
            "Tell me about pdf_renamer_by_isbn.py",
            "how to run pdf_renamer_by_isbn.py",
            "requirements for pdf_renamer_by_isbn.py",
            "arguments for pdf_renamer_by_isbn.py",
            "example for pdf_renamer_by_isbn.py",
            "describe amane_cut.py",
            "how do I execute amane_cut.py",
            "args for amane_cut.py",
            "what does amane_cut.py need?",
            "show me examples for amane_cut.py",
            "what about mogrify?",
            "how to run mogrify",
            "what are the requirements for mogrify",
            "tell me about jpg_to_ocr.py",
            "how to run pickle_to_serif_data.py",
            "what are the requirements for pickle_to_serif_data.py",
            "what is foobar script?",
            "exit" # This will be handled by the test loop, not the chatbot's internal exit
        ]
        
        transcript = "Welcome to the Yonkoma2Data Chatbot! Ask me about the scripts in this repository.\n"
        transcript += "You can ask things like 'What does amane_cut.py do?', 'How to run mogrify?', or 'arguments for pdf_renamer'.\n"
        transcript += "Type 'quit' or 'exit' to leave.\n"

        for query in test_queries:
            transcript += f"You: {query}\n"
            if query.lower() in ["quit", "exit"]:
                transcript += "Chatbot: Goodbye!\n"
                break
            
            mentioned_scripts = find_mentioned_scripts(query, SCRIPT_DATA)
            intent = identify_intent(query)
            response = generate_response(mentioned_scripts, intent, SCRIPT_DATA)
            transcript += f"Chatbot: {response}\n"
        
        print(transcript) # This will be the output for the subtask
        # --- End of testing block ---

        # Original interactive CLI (commented out for testing)
        # print("Welcome to the Yonkoma2Data Chatbot! Ask me about the scripts in this repository.")
        # print("You can ask things like 'What does amane_cut.py do?', 'How to run mogrify?', or 'arguments for pdf_renamer'.")
        # print("Type 'quit' or 'exit' to leave.")

        # while True:
        #     try:
        #         query = input("You: ").strip()
        #         if query.lower() in ["quit", "exit"]:
        #             print("Chatbot: Goodbye!")
        #             break
                
        #         if not query: 
        #             continue

        #         mentioned_scripts = find_mentioned_scripts(query, SCRIPT_DATA)
        #         intent = identify_intent(query)
                
        #         response = generate_response(mentioned_scripts, intent, SCRIPT_DATA)
        #         print(f"Chatbot: {response}")

        #     except EOFError: 
        #         print("\nChatbot: Goodbye!")
        #         break
        #     except KeyboardInterrupt: 
        #         print("\nChatbot: Goodbye! (Interrupted by user)")
        #         break
        #     except Exception as e:
        #         print(f"Chatbot: An unexpected error occurred: {e}. Please try again.")
        #         break
