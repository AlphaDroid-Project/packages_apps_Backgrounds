#!/usr/bin/env python3

import os
import subprocess
import sys
import argparse
from os.path import commonprefix
from pathlib import Path
import xml.etree.ElementTree as ET
import re

TARGET_DIR = "./res_walls/drawable-nodpi"
XML_FILE = "./res_walls/xml/wallpapers.xml"
STRINGS_FILE = "./res_walls/values/wallpaper_strings.xml"
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

def get_existing_string_names(strings_file):
    path = Path(strings_file)
    if not path.exists():
        return set()
    with open(strings_file, 'r', encoding='utf-8') as f:
        content = f.read()
    return set(re.findall(r'<string\s+name="([^"]+)"', content))

def filter_duplicate_strings(string_resources, existing_names):
    filtered = []
    skipped = 0
    for res in string_resources:
        m = re.search(r'name="([^"]+)"', res)
        if m and m.group(1) in existing_names:
            skipped += 1
            continue
        filtered.append(res)
        if m:
            existing_names.add(m.group(1))
    if skipped:
        print(f"skipped {skipped} duplicate string(s) already in strings file")
    return filtered

def insert_string_resources(strings_file, string_resources):
    strings_path = Path(strings_file)

    string_resources = filter_duplicate_strings(
        string_resources, get_existing_string_names(strings_file)
    )

    if not string_resources:
        print("no new strings to add.")
        return

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

def get_used_string_names_in_xml(xml_file):
    if not Path(xml_file).exists():
        return set()
    with open(xml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    return set(re.findall(r'@string/([A-Za-z0-9_]+)', content))

def get_referenced_drawables_in_xml(xml_file):
    return get_existing_drawables_in_xml(xml_file)

def merge_duplicate_categories(xml_file):
    if not Path(xml_file).exists():
        return

    with open(xml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = re.compile(
        r'[ \t]*<category\s+id="([^"]+)"[^>]*>(.*?)</category>\n?',
        re.DOTALL,
    )

    matches = list(pattern.finditer(content))
    if not matches:
        return

    by_id = {}
    for m in matches:
        by_id.setdefault(m.group(1), []).append(m)

    dups = {cid: ms for cid, ms in by_id.items() if len(ms) > 1}
    if not dups:
        return

    print(f"\nfound {len(dups)} duplicate categor(ies) to merge:")
    for cid, ms in dups.items():
        total = sum(len(re.findall(r'<static-wallpaper\b', m.group(2))) for m in ms)
        print(f"  - {cid}: {len(ms)} blocks, {total} total wallpapers")

    if input("\nmerge duplicate categories? (y/n): ").strip().lower() != 'y':
        return

    new_content = content
    for cid, ms in dups.items():
        first = ms[0]
        seen_ids = set(re.findall(r'<static-wallpaper\s+id="([^"]+)"', first.group(2)))
        merged_inner = first.group(2).rstrip()

        for extra in ms[1:]:
            for sw in re.finditer(
                r'\s*<static-wallpaper\b[^>]*?id="([^"]+)"[^>]*?(?:/>|>.*?</static-wallpaper>)',
                extra.group(2),
                re.DOTALL,
            ):
                wid = sw.group(1)
                if wid in seen_ids:
                    continue
                seen_ids.add(wid)
                merged_inner += "\n" + sw.group(0).lstrip('\n')

        merged_block = (
            re.match(r'[ \t]*<category\s+id="[^"]+"[^>]*>', first.group(0)).group(0)
            + merged_inner
            + "\n    </category>\n"
        )

        new_content = new_content.replace(first.group(0), merged_block, 1)
        for extra in ms[1:]:
            new_content = new_content.replace(extra.group(0), "", 1)

    with open(xml_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"merged {len(dups)} duplicate categor(ies).")

def repair():
    print("repair mode\n")

    issues = 0
    fixed = 0

    strings_path = Path(STRINGS_FILE)
    if not strings_path.exists():
        print(f"strings file missing: {STRINGS_FILE}")
        sys.exit(1)

    with open(STRINGS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    seen = {}
    dup_lines = []
    new_lines = []
    for line in content.splitlines():
        m = re.search(r'<string\s+name="([^"]+)"', line)
        if m:
            name = m.group(1)
            if name in seen:
                dup_lines.append(name)
                issues += 1
                fixed += 1
                continue
            seen[name] = True
        new_lines.append(line)

    if dup_lines:
        print(f"removing {len(dup_lines)} duplicate string(s):")
        for n in dup_lines:
            print(f"  - {n}")
        with open(STRINGS_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(new_lines) + ("\n" if content.endswith("\n") else ""))

    merge_duplicate_categories(XML_FILE)

    drawables_in_xml = get_referenced_drawables_in_xml(XML_FILE)
    webp_files = set(get_all_webp_files())

    missing_drawables = drawables_in_xml - webp_files
    if missing_drawables:
        issues += len(missing_drawables)
        print(f"\n{len(missing_drawables)} drawable(s) referenced in xml but missing on disk:")
        for d in sorted(missing_drawables):
            print(f"  - {d}")

    orphan_drawables = webp_files - drawables_in_xml
    if orphan_drawables:
        print(f"\n{len(orphan_drawables)} drawable(s) on disk not referenced in xml:")
        for d in sorted(orphan_drawables):
            print(f"  - {d}")

    used_strings = get_used_string_names_in_xml(XML_FILE)
    defined_strings = set(seen.keys())

    wallpaper_string_pattern = re.compile(r'^[a-z0-9_]+(_wallpaper)?$|_walls_title$')
    candidate_orphans = set()
    for name in defined_strings:
        if name in used_strings:
            continue
        if name.endswith('_walls_title') or name.endswith('_wallpaper'):
            candidate_orphans.add(name)
            continue
        if name + '_wallpaper' in defined_strings and name + '_wallpaper' not in used_strings:
            candidate_orphans.add(name)

    real_orphans = {n for n in candidate_orphans if n not in used_strings}
    if real_orphans:
        issues += len(real_orphans)
        print(f"\n{len(real_orphans)} wallpaper string(s) defined but not referenced by wallpapers.xml:")
        for n in sorted(real_orphans):
            print(f"  - {n}")
        if input("\nremove orphan strings? (y/n): ").strip().lower() == 'y':
            with open(STRINGS_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            kept = []
            removed = 0
            for line in content.splitlines():
                m = re.search(r'<string\s+name="([^"]+)"', line)
                if m and m.group(1) in real_orphans:
                    removed += 1
                    continue
                kept.append(line)
            with open(STRINGS_FILE, 'w', encoding='utf-8') as f:
                f.write("\n".join(kept) + "\n")
            fixed += removed
            print(f"removed {removed} orphan string(s).")

    print(f"\nrepair done. issues found: {issues}, fixed: {fixed}")

def main():
    parser = argparse.ArgumentParser(description="backgrounds regen script")
    parser.add_argument(
        "mode",
        nargs="?",
        default="add",
        choices=["add", "repair"],
        help="add: default flow, repair: fix duplicate/orphan strings",
    )
    args = parser.parse_args()

    if args.mode == "repair":
        repair()
        return

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
