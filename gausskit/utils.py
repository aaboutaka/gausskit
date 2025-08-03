import re


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

