import yaml
import datetime
import re
import sys
from pathlib import Path
import subprocess
import os
from gausskit.utils import MultiPathCompleter
from .utils import prompt_and_submit
from prompt_toolkit import prompt



def batch_fix_and_report():

    # 1) Choose logs
    all_logs = prompt(
        "Process ALL .log files in this directory? (y/N): "
    ).strip().lower().startswith('y')

    if all_logs:
        logfiles = sorted(f for f in os.listdir() if f.endswith('.log'))
    else:
        raw = prompt(
            "Enter comma-separated .log filenames: ",
            completer=MultiPathCompleter(file_filter=lambda f: f.endswith('.log'))
        ).strip()
        logfiles = [fn.strip() for fn in raw.split(',') if fn.strip()]

    if not logfiles:
        print("❌ No log files selected, aborting.")
        return

    # 2) Ask about resubmit
    resubmit = prompt(
        "Auto-resubmit SLURM job after fix? [y/N]: "
    ).strip().lower().startswith('y')

    # 3) Loop through each
    for logfile in logfiles:
        comfile = os.path.splitext(logfile)[0] + ".com"
        print(f"\n🔄 Fixing {logfile!r} → input {comfile!r}")
        fix_and_report(logfile, comfile, resubmit=resubmit)



def load_error_db():
    yaml_path = Path(__file__).parent / "gaussian_errors.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML error DB not found at: {yaml_path}")
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)


def extract_log_content(log_path, tail_bytes=10000):
    with open(log_path, "rb") as f:
        try:
            f.seek(-tail_bytes, os.SEEK_END)
        except OSError:
            f.seek(0)
        tail = f.read().decode(errors="ignore")
    return tail

#def extract_log_content(log_path):
#    with open(log_path, "r", errors="ignore") as f:
#        return f.read()

def match_errors(log_text, error_db):
    matched_errors = []
    for link, errors in error_db.items():
        for name, props in errors.items():
            for pattern in props["error_patterns"]:
                if re.search(pattern, log_text, re.IGNORECASE):
                    matched_errors.append((link, name, props["fix"], props["notes"]))
                    break
    return matched_errors


def apply_fixes(input_file: str, fix_dict: dict) -> str:
    """
    Apply SCF / route fixes to every Gaussian route line (#P).
    Returns the path to the backup file.
    """
    path = Path(input_file)
    orig_lines = path.read_text().splitlines()
    new_lines = []

    kws_remove = fix_dict.get("keywords_to_remove", [])
    kws_add    = fix_dict.get("keywords_to_add", [])

    # match any line that starts with '#' then 'p' (case-insensitive), e.g. "#P", "#p"
    route_re = re.compile(r'^\s*#\s*p', re.IGNORECASE)

    found_route = False

    print(f"🔍 Starting fixes in {input_file!r}")
    for idx, ln in enumerate(orig_lines, start=1):
        if route_re.match(ln):
            found_route = True
            print(f"\n🎯 Route line {idx}: {ln}")

            # 1) Remove unwanted keywords (in-line, not whole line)
            for kw in kws_remove:
                if re.search(re.escape(kw), ln, re.IGNORECASE):
                    ln = re.sub(re.escape(kw), '', ln, flags=re.IGNORECASE)
                    print(f"   ❌ Removed '{kw}'")
                else:
                    print(f"   ⚠️ Remove-keyword not found: '{kw}'")

            # collapse multiple spaces into one, split to tokens
            tokens = ln.split()
            # 2) Inject additions if missing
            for kw in kws_add:
                if not any(tok.lower() == kw.lower() for tok in tokens):
                    tokens.append(kw)
                    print(f"   ➕ Added '{kw}'")
                else:
                    print(f"   ℹ️ Skip add (already present): '{kw}'")

            # rebuild line
            ln = " ".join(tokens)

        new_lines.append(ln)

    if not found_route:
        print("⚠️ No route lines (#P) found – nothing injected.")
        return ""

    # 3) Backup and write
    bak = input_file + ".bak"
    Path(bak).write_text("\n".join(orig_lines))
    print(f"\n🛡️ Backup saved to {bak}")

    path.write_text("\n".join(new_lines))
    print(f"✅ Wrote fixed file: {input_file}")

    return bak



def fix_and_report(logfile, comfile, resubmit=False):
    db = load_error_db()
    log_text = extract_log_content(logfile)
    matches = match_errors(log_text, db)

    if not matches:
        print("✅ No known Gaussian errors detected.")
        return

    print("⚠️ Detected the following errors:")
    for link, err, fix, notes in matches:
        print(f"🔗 [{link}] {err}\n🧠 {notes.strip()}\n")

    first_fix = matches[0][2]
    
    # Skip fix if no meaningful changes required
    if (
        not first_fix.get("keywords_to_add")
        and not first_fix.get("keywords_to_remove")
        and not first_fix.get("lines_to_replace")
    ):
        print("ℹ️ No fixable keywords or modifications needed — skipping .com rewrite.")
    else:
        backup = apply_fixes(comfile, first_fix)
        print(f"\n✅ Applied fix. Backup saved to {backup}")
    
#    first_fix = matches[0][2]
#    backup = apply_fixes(comfile, first_fix)
#    print(f"\n✅ Applied fix. Backup saved to {backup}")

    if resubmit:
        prompt_and_submit(comfile)
    else:
        if prompt("Submit this fixed job to SLURM now? [y/N]: ").strip().lower().startswith("y"):
            prompt_and_submit(comfile)





#def submit_job(com_file, nproc=56, partition="medium", time=None, gdv="gdvj30+"):
#    filename = os.path.splitext(com_file)[0]
#    now = datetime.datetime.now()
#
#    # Auto-set time for test partition
#    if partition == "test" and not time:
#        time = "00:59:00"
#    elif not time:
#        time = "23:50:00"
#
#    gdv_modules = {
#        "g09": "gaussian/g09-d01",
#        "g16": "gaussian/g16-b01",
#        "gdvi10+": "gaussian/gdv-20170407-i10+",
#        "gdvj15": "gaussian/gdv-20210302-j15",
#        "gdvj26+": "gaussian/gdv-20240213-j26+",
#        "gdvj30+": "gaussian/gdv-20250101-j30+"
#    }
#    if gdv.lower() not in gdv_modules:
#        raise ValueError(f"Invalid GDV version: {gdv}")
#
#    Sname = f"Gscript.sh"
#    with open(Sname, 'w') as f:
#        f.write(f"""#!/bin/bash
##SBATCH --mail-user=$USER@ucmerced.edu
##SBATCH --mail-type=ALL
##SBATCH -J {filename}
##SBATCH -o {filename}.qlog
##SBATCH -p {partition}
##SBATCH --time={time}
##SBATCH --mem=115200
##SBATCH --nodes=1
##SBATCH --ntasks={nproc}
#
#module load {gdv_modules[gdv.lower()]}
#
#export My_Scratch=/scratch/$USER/$SLURM_JOBID
#export GAUSS_SCRDIR=$My_Scratch
#mkdir -p $My_Scratch
#
#gdv -m=92GB -p={nproc} < {com_file} >& {filename}.log
#
#rm -rf $My_Scratch
#
## Submitted at {now.strftime('%Y-%m-%d %H:%M:%S')}
#""")
#
#    subprocess.run(["chmod", "+x", Sname])
#    subprocess.run(["sbatch", Sname])
#    os.rename(Sname, f"{filename}.sbatch")
#    print(f"✅ Resubmitted via SLURM: {filename}.com → {filename}.sbatch")
#

