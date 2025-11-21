#!/usr/bin/env python3

import os
import subprocess
import sys
from os.path import commonprefix
from pathlib import Path
import xml.etree.ElementTree as ET
import re

TARGET_DIR = "./res_walls/drawable-nodpi"
XML_FILE = "./res_walls/xml/wallpapers.xml"
STRINGS_FILE = "./res/values/axion_strings.xml"
SUPPORTED_EXTENSIONS = ["png", "jpg", "jpeg"]

def sanitize_resource_name(text):
    text = re.sub(r'[ \-\.]', '_', text)
    text = re.sub(r'[^a-zA-Z0-9_]', '', text)
    text = re.sub(r'_+', '_', text)
    return text

def find_files_to_convert():
    files = []
    target_path = Path(TARGET_DIR)
    
    if not target_path.exists():
        print(f"directory {TARGET_DIR} does not exist.")
        sys.exit(1)
    
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(target_path.glob(f"*.{ext}"))
        files.extend(target_path.glob(f"*.{ext.upper()}"))
    
    return files

def convert_to_webp(files):
    if not files:
        print("no images to convert.")
        return []
    
    print(f"converting {len(files)} images to webp...")
    converted = []
    
    for file in files:
        webp_output = file.with_suffix('.webp')
        try:
            subprocess.run(['cwebp', str(file), '-o', str(webp_output)], 
                         check=True, capture_output=True)
            file.unlink()
            converted.append(webp_output.stem)
            print(f"converted: {file.name}")
        except subprocess.calledprocesserror as e:
            print(f"failed to convert {file.name}")
        except filenotfounderror:
            print("error: cwebp not found. install webp tools.")
            sys.exit(1)
    
    print(f"conversion completed. {len(converted)} files converted.")
    return converted

def get_all_webp_files():
    target_path = Path(TARGET_DIR)
    return [f.stem for f in target_path.glob("*.webp")]

def get_existing_drawables_in_xml(xml_file):
    if not Path(xml_file).exists():
        print(f"xml file {xml_file} does not exist.")
        sys.exit(1)
    
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        drawable_pattern = r'src="@drawable/([^"]+)"'
        matches = re.findall(drawable_pattern, content)
        
        return set(matches)
        
    except Exception as e:
        print(f"error parsing xml file: {e}")
        sys.exit(1)

def find_new_wallpapers(all_webp, existing_drawables):
    new_wallpapers = []
    
    for webp in all_webp:
        if webp not in existing_drawables:
            new_wallpapers.append(webp)
    
    return new_wallpapers

def analyze_wallpapers():
    all_webp = get_all_webp_files()
    existing_drawables = get_existing_drawables_in_xml(XML_FILE)
    
    print(f"\ntotal webp files: {len(all_webp)}")
    print(f"existing in xml: {len(existing_drawables)}")
    
    return all_webp, existing_drawables

from os.path import commonprefix

def extract_prefix_from_filenames(filenames):
    if not filenames:
        return ""

    prefix = commonprefix(filenames)

    last_underscore = prefix.rfind('_')
    if last_underscore > 0:
        prefix = prefix[:last_underscore]

    if not prefix:
        prefix = filenames[0].split('_')[0]

    return prefix

def group_wallpapers_by_prefix(wallpapers):
    wallpapers = sorted(wallpapers)
    groups = {}
    used = set()

    for i, wp in enumerate(wallpapers):
        if wp in used:
            continue

        group_members = [wp]
        used.add(wp)

        for other in wallpapers[i + 1:]:
            if other in used:
                continue

            prefix = commonprefix([wp, other])

            last_underscore = prefix.rfind('_')
            if last_underscore > 0:
                prefix = prefix[:last_underscore]

            if other.startswith(prefix) and len(prefix) > 1:
                group_members.append(other)
                used.add(other)

        if not prefix or len(prefix) <= 1:
            prefix = wp.split('_')[0]

        groups[prefix] = group_members

    return groups

def create_wall_string(text):
    text = text.replace('_', ' ').replace('-', ' ')
    text = ' '.join(word.capitalize() for word in text.split())
    return text

def get_grouping_choice(groups):
    print("\ndetected groupings:")
    
    for idx, (prefix, wallpapers) in enumerate(sorted(groups.items()), 1):
        print(f"\n{idx}. group '{prefix}' ({len(wallpapers)} wallpapers):")
        for wp in sorted(wallpapers)[:5]:
            print(f"   {wp}")
        if len(wallpapers) > 5:
            print(f"   ... and {len(wallpapers) - 5} more")
    
    print("\noptions:")
    print("1. group by detected prefixes")
    print("2. put all in one category")
    print("3. individual categories")
    
    while True:
        choice = input("\nChoose (1-3): ").strip()
        if choice in ['1', '2', '3']:
            return choice
        print("invalid choice.")

def generate_category_for_group(category_id, wallpapers):
    category_id_sanitized = sanitize_resource_name(category_id)
    category_title = f"@string/{category_id_sanitized}_title"
    
    lines = [f"\n    <category id=\"{category_id_sanitized}\" title=\"{category_title}\">"]
    
    for webp in sorted(wallpapers):
        wallpaper_title = f"@string/{sanitize_resource_name(webp)}"
        wallpaper_subtitle = f"@string/{sanitize_resource_name(webp)}_wallpaper"
        
        lines.append("        <static-wallpaper")
        lines.append(f"            id=\"{webp}\"")
        lines.append(f"            src=\"@drawable/{webp}\"")
        lines.append(f"            title=\"{wallpaper_title}\"")
        lines.append(f"            subtitle2=\"{wallpaper_subtitle}\"")
        lines.append("             />")
    
    lines.append("    </category>")
    
    return "\n".join(lines)

def generate_string_resources(category_id, wallpapers, wall_name):
    resources = []
    
    resources.append(f'    <string name="{sanitize_resource_name(category_id)}_title">{wall_name}</string>')

    for webp in wallpapers:
        res_name = sanitize_resource_name(webp)
        res_string = create_wall_string(webp)
        resources.append(f'    <string name="{res_name}">{res_string}</string>')
        resources.append(f'    <string name="{res_name}_wallpaper">{res_string} Wallpaper</string>')
    
    return resources

def find_root_closing_tag(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        return root.tag
    except Exception as e:
        print(f"error detecting root tag: {e}")
        return None

def insert_xml_entries(xml_file, new_entries):
    with open(xml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    root_tag = find_root_closing_tag(xml_file)
    
    if root_tag is None:
        print("error: could not detect root xml tag.")
        sys.exit(1)
    
    closing_tag = f"</{root_tag}>"
    
    if closing_tag not in content:
        print(f"error: could not find {closing_tag} closing tag.")
        sys.exit(1)
    
    last_index = content.rfind(closing_tag)
    modified_content = content[:last_index] + new_entries + "\n" + content[last_index:]
    
    with open(xml_file, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print("xml entries added.")

def insert_string_resources(strings_file, string_resources):
    strings_path = Path(strings_file)
    
    if strings_path.exists():
        print(f"appending to existing {strings_file}")
        
        with open(strings_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        root_tag = find_root_closing_tag(strings_file)
        if root_tag is None:
            print("error: could not detect root tag in strings file.")
            sys.exit(1)
        
        closing_tag = f"</{root_tag}>"
        
        if closing_tag not in content:
            print(f"error: could not find {closing_tag} in strings file.")
            sys.exit(1)
        
        last_index = content.rfind(closing_tag)
        new_strings = "\n" + "\n".join(string_resources) + "\n"
        modified_content = content[:last_index] + new_strings + content[last_index:]
        
        with open(strings_file, 'w', encoding='utf-8') as f:
            f.write(modified_content)
    else:
        print(f"creating new {strings_file}")
        
        strings_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(strings_file, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write('<resources>\n')
            for res in string_resources:
                f.write(res + '\n')
            f.write('</resources>\n')
    
    print(f"string resources added to {strings_file}")

def main():
    print("backgrounds regen script\n")
    
    files_to_convert = find_files_to_convert()
    newly_converted = convert_to_webp(files_to_convert)
    
    all_webp, existing_drawables = analyze_wallpapers()
    
    new_wallpapers = find_new_wallpapers(all_webp, existing_drawables)
    
    if not new_wallpapers:
        print("\nnothing to add...")
        sys.exit(0)
    
    print(f"\nfound {len(new_wallpapers)} new wallpapers:")
    for wp in sorted(new_wallpapers):
        print(f"  {wp}.webp")
    
    groups = group_wallpapers_by_prefix(new_wallpapers)
    
    choice = get_grouping_choice(groups)
    
    all_entries = []
    all_string_resources = []
    
    if choice == '1':
        print("\ngenerating entries...")
        
        for prefix, wallpapers in sorted(groups.items()):
            category_id = f"{prefix}_walls"
            wall_name = create_wall_string(prefix)
            
            print(f"category: {category_id} ({len(wallpapers)} wallpapers)")
            
            entry = generate_category_for_group(category_id, wallpapers)
            all_entries.append(entry)
            
            string_res = generate_string_resources(category_id, wallpapers, wall_name)
            all_string_resources.extend(string_res)
    
    elif choice == '2':
        category_name = input("\ncategory name: ").strip()
        if not category_name:
            category_name = "new_walls"
        
        category_id = category_name if category_name.endswith('_walls') else f"{category_name}_walls"
        wall_name = create_wall_string(category_name.replace('_walls', ''))
        
        print(f"creating category: {category_id}")
        
        entry = generate_category_for_group(category_id, new_wallpapers)
        all_entries.append(entry)
        
        string_res = generate_string_resources(category_id, new_wallpapers, wall_name)
        all_string_resources.extend(string_res)
    
    else:
        print("\ncreating individial categories...")
        
        for wp in sorted(new_wallpapers):
            category_id = f"{wp}_wall"
            wall_name = create_wall_string(wp)
            
            entry = generate_category_for_group(category_id, [wp])
            all_entries.append(entry)
            
            string_res = generate_string_resources(category_id, [wp], wall_name)
            all_string_resources.extend(string_res)
    
    combined_entries = "".join(all_entries)
    
    print("\npreview:")
    print(combined_entries[:500])
    if len(combined_entries) > 500:
        print("...")
    
    proceed = input("\nproceed? (y/n): ").strip().lower()
    if proceed != 'y':
        print("cancelled.")
        sys.exit(0)
    
    insert_xml_entries(XML_FILE, combined_entries)
    
    insert_string_resources(STRINGS_FILE, all_string_resources)
    
    print(f"\ndone. added {len(new_wallpapers)} wallpapers in {len(all_entries)} categories.")

if __name__ == "__main__":
    main()
