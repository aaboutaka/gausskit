import re

from prompt_toolkit.completion import Completer, PathCompleter, Completion
from prompt_toolkit.completion import FuzzyCompleter, WordCompleter

class HybridCompleter(FuzzyCompleter):
    def __init__(self, completers):
        super().__init__(completers[0])  # Customize if chaining


class MultiPathCompleter(Completer):
    """
    Like PathCompleter, but will complete *after* commas.
    Splits the input on commas and only asks PathCompleter to complete
    the last token, then replaces that token when you hit TAB.
    """
    def __init__(self, **kwargs):
        # delegate everything to a normal PathCompleter
        self._inner = PathCompleter(**kwargs)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        if ',' in text:
            # split off everything up to the last comma
            prefix, last = text.rsplit(',', 1)
            stripped = last.lstrip()
            replace_len = len(last)

            # make a fake document for just that last segment
            class _Doc:
                def __init__(self, txt):
                    self.text_before_cursor = txt

            fake = _Doc(stripped)
            for c in self._inner.get_completions(fake, complete_event):
                yield Completion(
                    c.text,
                    start_position=-replace_len
                )
        else:
            # no commas yet — act just like PathCompleter
            yield from self._inner.get_completions(document, complete_event)





def parse_swap_pairs(swap_string):
    if not swap_string:
        return []
    pairs = [pair.strip() for pair in swap_string.split(',') if pair.strip()]
    return [pair.split() for pair in pairs]


def is_gaussian_terminated(filepath, lines_to_check=100):
    """
    Checks if Gaussian log file terminated normally.
    If not, attempts to return a minimal error message (e.g., Link1e, memory).
    Returns (True, None) if normal, else (False, 'Error snippet')
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Check for normal termination
        for line in reversed(lines[-lines_to_check:]):
            if "Normal termination of Gaussian" in line:
                return True, None

        # Look for error snippet
        error = None
        for line in reversed(lines[-lines_to_check:]):
            if "Error termination" in line or "Error" in line or "exit code" in line:
                error = line.strip()
                break
            if "Link1e" in line or "l9999.exe" in line:
                error = line.strip()
                break
        return False, error or "Unknown error"

    except Exception as e:
        return False, f"I/O error: {e}"


def extract_energy(filepath, method="scf"):
    """
    Extracts energy from a Gaussian log file based on specified method.
    Supported: scf, zpe, mp2, pm2, pmp2, pmp2-0.
    Returns (energy, [recent SCF values]) or (None, None) on failure.
    """
    energy = None
    raw = []
    method = method.lower()

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️ Error reading {filepath}: {e}")
        return None, None

    if method == "zpe":
        for line in lines:
            if "Sum of electronic and zero-point Energies=" in line:
                match = re.search(r"= *(-?\d+\.\d+)", line)
                if match:
                    energy = float(match.group(1))
                    break

    elif method == "scf":
        for line in lines:
            if "SCF Done" in line:
                match = re.search(r'SCF Done:\s+E\([^)]+\)\s*=\s*(-?\d+\.\d+)', line)
                if match:
                    raw.append(float(match.group(1)))
        if raw:
            energy = raw[-1]

    elif method in ("mp2", "pm2", "pmp2", "pmp2-0"):
        combined = ''.join(line.strip() for line in lines[-100:])
        pattern = rf'\\{method.upper()}[-0]*=([-]?\d+\.\d+)'
        match = re.search(pattern, combined)
        if match:
            energy = float(match.group(1))
        else:
            print(f"❌ Could not find {method.upper()} energy in {filepath}")

    else:
        raise ValueError(f"Unsupported energy method: {method}")

    return energy, raw[-2:] if raw else None


def _log_skipped(logfile, message):
    with open(logfile, "a") as f:
        f.write(message + "\n")

def hartree_to_ev(h):
    return h * 27.2114



def submit_job(com_file, nproc=56, partition="medium", time=None, gdv="gdvj30+"):
    filename = os.path.splitext(com_file)[0]
    now = datetime.datetime.now()

    # Auto-set time for test partition
    if partition == "test" and not time:
        time = "00:59:00"
    elif not time:
        time = "23:50:00"

    gdv_modules = {
        "g09": "gaussian/g09-d01",
        "g16": "gaussian/g16-b01",
        "gdvi10+": "gaussian/gdv-20170407-i10+",
        "gdvj15": "gaussian/gdv-20210302-j15",
        "gdvj26+": "gaussian/gdv-20240213-j26+",
        "gdvj30+": "gaussian/gdv-20250101-j30+"
    }
    if gdv.lower() not in gdv_modules:
        raise ValueError(f"Invalid GDV version: {gdv}")

    Sname = f"Gscript.sh"
    with open(Sname, 'w') as f:
        f.write(f"""#!/bin/bash
#SBATCH --mail-user=$USER@ucmerced.edu
#SBATCH --mail-type=ALL
#SBATCH -J {filename}
#SBATCH -o {filename}.qlog
#SBATCH -p {partition}
#SBATCH --time={time}
#SBATCH --mem=115200
#SBATCH --nodes=1
#SBATCH --ntasks={nproc}

module load {gdv_modules[gdv.lower()]}

export My_Scratch=/scratch/$USER/$SLURM_JOBID
export GAUSS_SCRDIR=$My_Scratch
mkdir -p $My_Scratch

gdv -m=92GB -p={nproc} < {com_file} >& {filename}.log

rm -rf $My_Scratch

# Submitted at {now.strftime('%Y-%m-%d %H:%M:%S')}
""")

    subprocess.run(["chmod", "+x", Sname])
    subprocess.run(["sbatch", Sname])
    os.rename(Sname, f"{filename}.sbatch")
    print(f"✅ Resubmitted via SLURM: {filename}.com → {filename}.sbatch")


import os, datetime, subprocess
from prompt_toolkit import prompt

GDV_MODULES = {
    "g09":    "gaussian/g09-d01",
    "g16":    "gaussian/g16-b01",
    "gdvi10+":"gaussian/gdv-20170407-i10+",
    "gdvj15": "gaussian/gdv-20210302-j15",
    "gdvj26+":"gaussian/gdv-20240213-j26+",
    "gdvj30+":"gaussian/gdv-20250101-j30+",
}

def prompt_slurm_params():
    gdv_key = prompt(f"Gaussian command ({'/'.join(GDV_MODULES)}) [gdvj30+]: ").strip() or "gdvj30+"
    if gdv_key not in GDV_MODULES:
        print(f"⚠️ Unknown Gaussian '{gdv_key}', defaulting to gdvj30+")
        gdv_key = "gdvj30+"

    partition = prompt("Partition [medium]: ").strip() or "medium"
    time_lim  = prompt("Time limit (HH:MM:SS) [23:50:00]: ").strip() or "23:50:00"
    nproc     = prompt("Number of tasks/processors [56]: ").strip() or "56"

    return int(nproc), partition, time_lim, gdv_key

def prompt_and_submit(com_file: str):
    if not prompt(f"Submit {com_file} to SLURM? [y/N]: ").strip().lower().startswith("y"):
        print("→ Skipping SLURM submission.")
        return

    nproc, partition, time_lim, gdv_key = prompt_slurm_params()
    submit_job(
        com_file,
        nproc=nproc,
        partition=partition,
        time=time_lim,
        gdv=gdv_key
    )

