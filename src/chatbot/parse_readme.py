import json
import re
import os

def parse_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "..", "..", "README.md")
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(json.dumps({"error": "README.md not found"}, ensure_ascii=False))
        return

    extracted_data = []
    
    scripts_to_process_ordered = [
        "pdf_renamer_by_isbn.py",
        "pdf_to_pages.py",
        "mogrify",
        "amane_cut.py",
        "jpg_to_ocr.py",
        "pickle_to_serif_data.py"
    ]
    
    section_titles_map = {
        "pdf_renamer_by_isbn.py": "PDFファイルのバーコード（JANコード）を読み取り自動リネーム",
        "pdf_to_pages.py": "PDFファイルをページ毎のPNGファイルに切り出す",
        "mogrify": "傾き補正、美白化を行う",
        "amane_cut.py": "ページ毎のJPGファイルを1コマ毎のJPGファイルに切り出す。多くの作品に対応版",
        "jpg_to_ocr.py": "画像をOCRをにかける",
        "pickle_to_serif_data.py": "OCR結果を綺麗にしてcsv出力"
    }

    raw_major_sections = content.split("\n## ")
    raw_major_sections.pop(0) 

    readme_major_sections_map = {}
    for section_block_text in raw_major_sections:
        full_section_text = "## " + section_block_text
        block_lines = full_section_text.strip().split('\n')
        if not block_lines: continue
        current_block_title = block_lines[0].lstrip('# ').strip()
        readme_major_sections_map[current_block_title] = full_section_text

    script_content_blocks = {} 
    for key in scripts_to_process_ordered:
        target_title = section_titles_map[key]
        if key in ["jpg_to_ocr.py", "pickle_to_serif_data.py"]: 
            parent_section_text = readme_major_sections_map.get("コマ中のセリフを抽出する")
            if parent_section_text:
                match = re.search(rf"###\s*{re.escape(target_title)}\s*\n(.*?)(?=\n###\s|\n##|$)", parent_section_text, re.DOTALL)
                if match:
                    script_content_blocks[key] = f"### {target_title}\n" + match.group(1).strip()
        else: 
            script_content_blocks[key] = readme_major_sections_map.get(target_title)

    shared_ocr_requirements = []
    ocr_parent_text = readme_major_sections_map.get("コマ中のセリフを抽出する")
    if ocr_parent_text:
        req_match = re.search(r"### require\n(.*?)(?=\n###|\n##|$)", ocr_parent_text, re.DOTALL | re.IGNORECASE)
        if req_match:
            shared_ocr_requirements = [line.strip().lstrip("- ") for line in req_match.group(1).strip().split('\n') if line.strip()]

    for script_key in scripts_to_process_ordered:
        if not script_content_blocks.get(script_key):
            extracted_data.append({"script_name": script_key, "title": section_titles_map.get(script_key, script_key), "description": "Error: Content block not found.", "requirements": [], "run_command": "", "arguments": [], "example_usage": ""})
            continue

        block_text = script_content_blocks[script_key]
        lines = block_text.strip().split('\n')

        data = {
            "script_name": script_key,
            "title": lines[0].lstrip("# ").lstrip("### ").strip(), 
            "description": "", "requirements": [], "run_command": "", "arguments": [], "example_usage": ""
        }
        
        content_after_title = "\n".join(lines[1:])

        # --- Requirements ---
        if script_key in ["jpg_to_ocr.py", "pickle_to_serif_data.py"]:
            data["requirements"] = shared_ocr_requirements
        else: 
            req_match = re.search(r"### require\n(.*?)(?=\n###|\n##|$)", content_after_title, re.DOTALL | re.IGNORECASE)
            if req_match:
                data["requirements"] = [line.strip().lstrip("- ") for line in req_match.group(1).strip().split('\n') if line.strip()]

        # --- Run Command ---
        if script_key not in ["mogrify", "jpg_to_ocr.py", "pickle_to_serif_data.py"]:
            run_section_match = re.search(r"### run\n(.*?)(?=\n###|\n##|$)", content_after_title, re.DOTALL | re.IGNORECASE)
            if run_section_match:
                run_text = run_section_match.group(1).strip()
                cmd_match = re.search(r"`\$\s*(.+?)`", run_text, re.DOTALL)
                if cmd_match: data["run_command"] = cmd_match.group(1).strip()
                else: data["run_command"] = run_text.split('\n')[0].strip().lstrip("$ ").strip()
        
        if not data["run_command"]: # Fallbacks for specific scripts
            if script_key == "mogrify":
                cmd_match = re.search(r"`\$\s*(mogrify .*?)`", content_after_title, re.DOTALL)
                if cmd_match: data["run_command"] = cmd_match.group(1).strip().lstrip("`$ ").rstrip("`")
            elif script_key == "jpg_to_ocr.py":
                cmd_match = re.search(r"`\$\s*(python3? jpg_to_ocr\.py.*?)`", content_after_title, re.DOTALL)
                if cmd_match: data["run_command"] = cmd_match.group(1).strip()
            elif script_key == "pickle_to_serif_data.py":
                cmd_match = re.search(r"`\$\s*(python3? pickle_to_serif_data\.py.*?)`", content_after_title, re.DOTALL)
                if cmd_match: data["run_command"] = cmd_match.group(1).strip()
        
        # --- Description ---
        if script_key in ["pdf_renamer_by_isbn.py", "pdf_to_pages.py", "amane_cut.py"]:
            # Description is text after "## Title" and strictly before the first "\n###"
            # content_after_title is the full text block after "## Title".
            # We split this block by the first occurrence of "\n### ".
            desc_parts = content_after_title.split("\n### ", 1)
            # The first part is the description. If no "### " is found, this is the whole content_after_title.
            potential_description = desc_parts[0].strip()
            # Check if this potential description contains a "### require" or "### run" etc.
            # This can happen if "### require" is the very first thing after the title.
            if potential_description.startswith("### "): # Unlikely with split, but as safeguard
                 data["description"] = ""
            else:
                 data["description"] = potential_description

        elif script_key == "mogrify":
            desc_text = content_after_title
            if data["run_command"] and data["run_command"] in desc_text: 
                 desc_text = desc_text.split(data["run_command"], 1)[-1]
            desc_text = re.sub(r"`\$\s*cd .*?`\s*\n?", "", desc_text).strip() 
            # Capture "- 以下の値は適宜調整する" and all subsequent lines starting with "    -" or "-" up to an empty line or next heading
            options_match = re.search(r"(- 以下の値は適宜調整する\s*(?:\n\s*-\s[^\n]*)*)", desc_text, re.MULTILINE)
            if options_match:
                data["description"] = options_match.group(1).strip()
            else:
                data["description"] = desc_text.strip() 
        elif script_key == "jpg_to_ocr.py":
            desc_match = re.search(r"(OCR結果は\s*`path/to/pickle/image_dir_path\(_master\)\.pickle`\s*に保存されます\.)", content_after_title)
            if desc_match:
                data["description"] = desc_match.group(1).strip()
            else: # Fallback if specific sentence not found
                if data["run_command"] and data["run_command"] in content_after_title:
                    data["description"] = content_after_title.split(data["run_command"])[0].strip()
                elif "###" not in content_after_title: # If no other subsections, take all
                     data["description"] = content_after_title.strip()
                else:
                    data["description"] = "" 
        elif script_key == "pickle_to_serif_data.py":
            if data["run_command"] and data["run_command"] in content_after_title:
                desc_text_candidate = content_after_title.split(data["run_command"])[0].strip()
                # Only accept if it doesn't look like a leftover command or heading
                if not desc_text_candidate.startswith("`$") and not desc_text_candidate.startswith("###"):
                    data["description"] = desc_text_candidate
                else:
                    data["description"] = ""
            else: # If no run command, and if content_after_title is not a heading itself
                if not content_after_title.startswith("###"):
                    data["description"] = content_after_title.strip()
                else:
                    data["description"] = ""


        # --- Arguments (for amane_cut.py) ---
        if script_key == "amane_cut.py":
            args_match = re.search(r"### args\n(.*?)(?=\n#### args run exmaple|\n###|\n##|$)", content_after_title, re.DOTALL | re.IGNORECASE)
            if args_match:
                args_table_text = args_match.group(1).strip()
                arg_lines = [line.strip() for line in args_table_text.split('\n') if line.strip().startswith('|')]
                header_skipped, separator_skipped = False, False
                for arg_line in arg_lines:
                    cols = [col.strip() for col in arg_line.strip('|').split('|')]
                    if not header_skipped and "args name" in cols[0].lower(): header_skipped = True; continue
                    if not separator_skipped and "-------" in cols[0]: separator_skipped = True; continue
                    if header_skipped and separator_skipped and len(cols) >= 1:
                        arg_data = {"arg": cols[0], "default": cols[1] if len(cols) > 1 else "", "description": cols[2] if len(cols) > 2 else ""}
                        data["arguments"].append(arg_data)
        
        if script_key == "amane_cut.py":
            amane_full_block = readme_major_sections_map.get(section_titles_map["amane_cut.py"], "")
            example_match = re.search(r"#### args run exmaple\n(.*?)(?=\n###|\n##|$)", amane_full_block, re.DOTALL | re.IGNORECASE)
            if example_match:
                examples_text = example_match.group(1).strip()
                example_cmds = re.findall(r"(?:`\$\s*.*?`|^\s*python.*)", examples_text, re.MULTILINE)
                data["example_usage"] = "\n".join([cmd.strip().lstrip('`$ ').rstrip('`') for cmd in example_cmds if cmd.strip()])
                if not data["example_usage"] and examples_text: data["example_usage"] = examples_text

        extracted_data.append(data)

    print(json.dumps(extracted_data, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    parse_readme()
