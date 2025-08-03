import yaml
import re
import sys
from pathlib import Path

def load_error_db(yaml_path="gaussian_errors.yaml"):
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)

def extract_log_content(log_path):
    with open(log_path, "r", errors="ignore") as f:
        return f.read()

def match_errors(log_text, error_db):
    matched_errors = []
    for link, errors in error_db.items():
        for name, props in errors.items():
            for pattern in props["error_patterns"]:
                if re.search(pattern, log_text, re.IGNORECASE):
                    matched_errors.append((link, name, props["fix"], props["notes"]))
                    break
    return matched_errors


def apply_fixes(input_file, fix_dict):
    lines = Path(input_file).read_text().splitlines()
    new_lines = []

    for line in lines:
        skip_line = False
        for remove_kw in fix_dict.get("keywords_to_remove", []):
            if remove_kw in line:
                skip_line = True
        if not skip_line:
            new_lines.append(line)

    # Replace lines
    for repl in fix_dict.get("lines_to_replace", []):
        new_lines = [re.sub(repl["old"], repl["new"], ln) for ln in new_lines]

    # Replace keywords
    for repl in fix_dict.get("keywords_to_replace", []):
        new_lines = [re.sub(repl["old"], repl["new"], ln) for ln in new_lines]

    # Inject keywords
    if fix_dict.get("inject_into"):
        idx = next((i for i, ln in enumerate(new_lines) if fix_dict["inject_into"] in ln), None)
        if idx is not None:
            for kw in fix_dict.get("keywords_to_add", []):
                new_lines.insert(idx + 1, kw)
    else:
        new_lines.extend(fix_dict.get("keywords_to_add", []))

    # Save
    backup_path = input_file + ".bak"
    Path(backup_path).write_text("\n".join(lines))
    Path(input_file).write_text("\n".join(new_lines))

    return backup_path


def fix_and_report(logfile, comfile):
    db = load_error_db()
    log_text = extract_log_content(logfile)
    matches = match_errors(log_text, db)

    if not matches:
        print("✅ No known Gaussian errors detected.")
        return

    print("⚠️ Detected the following errors:")
    for link, err, fix, notes in matches:
        print(f"🔗 [{link}] {err}\n🧠 {notes.strip().splitlines()[0]}\n")

    # Apply first fix only (or extend to multi-fix logic)
    first_fix = matches[0][2]
    backup = apply_fixes(comfile, first_fix)
    print(f"\n✅ Applied fix. Backup saved to {backup}")



