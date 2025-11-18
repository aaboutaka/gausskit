import os
import re
import csv
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter
from gausskit.completions import tab_autocomplete_prompt
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from .utils import (
    is_gaussian_terminated,
    extract_scan_variables_from_com,
    extract_energy,
    hartree_to_ev,
    MultiPathCompleter
)
from .filename_parser import FilenameParser  # Assuming you save as separate module



def extract_log_summary(logfile):
    """
    Parse a Gaussian log file and return a dict of metrics.
    """
    summary = {
        'logfile': logfile,
        'scf_energy': None,
        'homo_alpha': None, 'lumo_alpha': None,
        'homo_beta': None,  'lumo_beta': None,
        'zpe_corr': None, 'enthalpy_corr': None,
        'freqs': [], 'ir_intens': [], 'imag_freqs': 0,
        'excitations': [], 'max_force': None, 'rms_force': None,
        'dip_x': None, 'dip_y': None, 'dip_z': None, 'dip_tot': None,
        'functional': None, 'basis': None,
        'charge': None, 'multiplicity': None,    # ensure these exist
        'mem': None, 'cpu_time': None, 'wall_time': None,
        'job_types': set(), 'scf_warnings': [], 'spin_contam': None
    }

    with open(logfile, 'r', errors='ignore') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        text = line.strip()

        # --- Route section & job types ---
        if text.lower().startswith('#p'):
            parts = text.split()
            rt = ' '.join(parts[1:])
            if '/' in parts[1]:
                summary['functional'], summary['basis'] = parts[1].split('/', 1)
            for kt, jt in [
                ('opt', 'Optimization'),
                ('freq','Frequency'),
                ('td(', 'TDDFT'),
                ('pimom','PIMOM'),
                ('sp','Single-point'),
                ('stable','Stability')
            ]:
                if kt in rt.lower():
                    summary['job_types'].add(jt)

        # --- Memory & CPU procs ---
        if text.lower().startswith('%mem='):
            summary['mem'] = text.split('=', 1)[1]
        if text.lower().startswith('%nproc'):
            summary['cpu_time'] = text.split('=', 1)[1]

        # --- Charge & Multiplicity ---
        # strip off any leading “/ ” or other junk before matching
        clean = line.strip().lstrip('/').lstrip()
        m = re.search(
            r'Charge\s*=\s*([+-]?\d+)\s+Multiplicity\s*=\s*([+-]?\d+)',
            clean,
            flags=re.IGNORECASE
        )
        if m:
            # **FIXED HERE**: actually assign into summary dict
            summary['charge']       = int(m.group(1))
            summary['multiplicity'] = int(m.group(2))

        # --- SCF energy & warnings ---
        m = re.search(r'SCF Done:\s+E\(\w+\)\s+=\s+(-?\d+\.\d+)', line)
        if m:
            summary['scf_energy'] = float(m.group(1))
        if 'SCF failed to converge' in line or 'Convergence failure' in line:
            summary['scf_warnings'].append(text)

        # --- HOMO/LUMO α & β ---
        if "Alpha  occ. eigenvalues" in line:
            occ = [float(x) for x in line.split('--')[-1].split()
                   if re.match(r'[-+]?\d*\.\d+', x)]
            if occ:
                summary['homo_alpha'] = occ[-1]
        if ("Alpha virt. eigenvalues" in line
            and summary['homo_alpha'] is not None
            and summary['lumo_alpha'] is None):
            virt = [float(x) for x in line.split('--')[-1].split()
                    if re.match(r'[-+]?\d*\.\d+', x)]
            if virt:
                summary['lumo_alpha'] = virt[0]

        if "Beta  occ. eigenvalues" in line:
            occ = [float(x) for x in line.split('--')[-1].split()
                   if re.match(r'[-+]?\d*\.\d+', x)]
            if occ:
                summary['homo_beta'] = occ[-1]
        if ("Beta virt. eigenvalues" in line
            and summary['homo_beta'] is not None
            and summary['lumo_beta'] is None):
            virt = [float(x) for x in line.split('--')[-1].split()
                    if re.match(r'[-+]?\d*\.\d+', x)]
            if virt:
                summary['lumo_beta'] = virt[0]

        # --- ZPE & Thermal Enthalpy ---
        m = re.search(r'Zero-point correction=\s+([-\d\.]+)', line)
        if m:
            summary['zpe_corr'] = float(m.group(1))
        m = re.search(r'Thermal correction to Enthalpy=\s+([-\d\.]+)', line)
        if m:
            summary['enthalpy_corr'] = float(m.group(1))

        # --- Frequencies & IR intensities ---
        if text.startswith("Frequencies --"):
            vals = [float(x) for x in text.split()[2:]
                    if re.match(r'[-+]?\d*\.\d+', x)]
            summary['freqs'].extend(vals)
            summary['imag_freqs'] += sum(1 for v in vals if v < 0)
        if text.startswith("IR Inten"):
            vals = [float(x) for x in text.split()[3:]
                    if re.match(r'[-+]?\d*\.\d+', x)]
            summary['ir_intens'].extend(vals)

        # --- TDDFT excitations & spin contamination ---
        m = re.search(
            r'Excited State\s+(\d+):\s+\S+\s+([-+]?\d*\.\d+)\s*eV.*?f=([-+]?\d*\.\d+)',
            line
        )
        if m:
            st, en, fstr = m.groups()
            summary['excitations'].append((int(st), float(en), float(fstr)))
        # Track candidate S² values
        spin_vals = []
        
        # Detect SCF Done blocks to look nearby for <S**2>
        if "SCF Done:" in line:
            # Look ahead a few lines
            for j in range(1, 6):
                if i + j >= len(lines):
                    break
                lookahead = lines[i + j]
                if "<S**2>" in lookahead:
                    sm = re.search(r'<S\*\*2>\s*=\s*([\d\.]+)', lookahead)
                    if sm:
                        val = float(sm.group(1))
                        spin_vals.append(val)
#                        print(f"🔍 [DEBUG] Found ⟨S²⟩ = {val:.4f} in lookahead (line {i + j + 1}) after SCF Done")
#                        print(f"      ↳ Line: {lookahead.strip()}")
                        break
        
        # Match line like: S**2 before annihilation    24.2562,   after    45.5039
        if "S**2 before annihilation" in line:
            match = re.search(r'before\s+([\d\.]+),\s+after\s+([\d\.]+)', line)
            if match:
                before_val = float(match.group(1))
                after_val  = float(match.group(2))
                spin_vals.append(after_val)
       #         print(f"🔍 [DEBUG] Found ⟨S²⟩ = {after_val:.4f} from annihilation line (line {i+1})")
       #         print(f"      ↳ Line: {line.strip()}")
        if spin_vals:
            summary['spin_contam'] = spin_vals[-1]  # use last seen value (often final)

        

        # --- Convergence Forces ---
        if 'Maximum Force' in text and 'Threshold' in text:
            summary['max_force'] = float(text.split()[2])
        if 'RMS     Force' in text:
            summary['rms_force'] = float(text.split()[2])

        # --- Dipole moment ---
        if 'Dipole moment (field-independent' in line:
            nxt = lines[i+1].strip()
            m = re.findall(r'[-+]?\d*\.\d+', nxt)
            if len(m) >= 4:
                summary['dip_x'], summary['dip_y'], summary['dip_z'], summary['dip_tot'] = map(float, m[:4])

        # --- Timing info ---
        if 'Job cpu time:' in line:
            summary['cpu_time'] = line.split(':',1)[1].strip()
        if 'Elapsed time:' in line:
            summary['wall_time'] = line.split(':',1)[1].strip()

    return summary

def write_summary_csv(summary, csv_file):
    """
    Write a single-summary CSV.
    """
    with open(csv_file, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Metric', 'Value'])
        for k, v in summary.items():
            if k == 'logfile': 
                continue
            if isinstance(v, list):
                v = ';'.join(str(x) for x in v)
            elif isinstance(v, set):
                v = ';'.join(sorted(v))
            w.writerow([k, v])

def write_combined_csv(summaries, csv_file):
    """
    Write a combined CSV for multiple summaries.
    """
    if not summaries:
        return
    keys = [k for k in summaries[0] if k != 'logfile']
    with open(csv_file, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['logfile'] + keys)
        for s in summaries:
            row = [s['logfile']]
            for k in keys:
                v = s[k]
                if isinstance(v, list):
                    v = ';'.join(str(x) for x in v)
                elif isinstance(v, set):
                    v = ';'.join(sorted(v))
                row.append(v)
            w.writerow(row)

def analyze_log(logfile):
    """
    Print human-readable summary for one log file.
    """
    summary = extract_log_summary(logfile)
    print("\n🔍 Log Analysis Summary")
    if summary['functional'] and summary['basis']:
        print(f" • Route         : {summary['functional']}/{summary['basis']}")
    if summary['charge'] is not None and summary['multiplicity'] is not None:
        print(f" • Charge/Mult   : {summary['charge']}/{summary['multiplicity']}")
    if summary['mem']:
        print(f" • %Mem          : {summary['mem']}")
    if summary['cpu_time']:
        print(f" • CPU Time      : {summary['cpu_time']}")
    if summary['wall_time']:
        print(f" • Wall Time     : {summary['wall_time']}")
    if summary['scf_energy'] is not None:
        print(f" • SCF Energy    : {summary['scf_energy']:.6f} au")
    if summary['scf_warnings']:
        print(f" ⚠️ SCF Warnings  : {'; '.join(summary['scf_warnings'])}")
    if summary['homo_alpha'] is not None and summary['lumo_alpha'] is not None:
        raw = summary['lumo_alpha'] - summary['homo_alpha']
        if abs(raw) < 5:
            ev = raw * 27.2114
            print(f" • α–Gap         : {raw:.6f} au → {ev:.3f} eV")
        else:
            print(f" • α–Gap         : {raw:.3f} eV")
    if summary['homo_beta'] is not None and summary['lumo_beta'] is not None:
        raw = summary['lumo_beta'] - summary['homo_beta']
        if abs(raw) < 5:
            ev = raw * 27.2114
            print(f" • β–Gap         : {raw:.6f} au → {ev:.3f} eV")
        else:
            print(f" • β–Gap         : {raw:.3f} eV")
    if summary['zpe_corr'] is not None:
        print(f" • ZPE Corr      : {summary['zpe_corr']:.6f} au")
    if summary['enthalpy_corr'] is not None:
        print(f" • Enthalpy Corr : {summary['enthalpy_corr']:.6f} au")
    if summary['freqs']:
        print(f" • Frequencies   : {len(summary['freqs'])} modes, {summary['imag_freqs']} imag.")
        print(f"    cm⁻¹: {', '.join(f'{f:.1f}' for f in summary['freqs'])}")
        print(f"    IR  : {', '.join(f'{i:.1f}' for i in summary['ir_intens'])}")
    if summary['excitations']:
        print(" • TDDFT Excitations:")
        for st, en, f in summary['excitations']:
            print(f"    → State {st}: {en:.3f} eV (f = {f:.3g})")
    if summary['dip_tot'] is not None:
        print(f" • Dipole        : X={summary['dip_x']:.4f}  Y={summary['dip_y']:.4f}  Z={summary['dip_z']:.4f}  Tot={summary['dip_tot']:.4f} D")
    if summary['max_force'] is not None and summary['rms_force'] is not None:
        print(f" • Forces        : Max={summary['max_force']:.6f}  RMS={summary['rms_force']:.6f}")
#    if summary['spin_contam'] is not None:
#        print(f" ⚠️ Spin Contam.  : ⟨S²⟩={summary['spin_contam']:.4f}")

    if summary["spin_contam"] is not None:
        multiplicity = summary.get("multiplicity")
        if multiplicity:
            try:
                ideal_s2 = ((int(multiplicity) - 1)*(int(multiplicity) + 1) / 4) 
                actual_s2 = summary["spin_contam"]
                delta_s2 = actual_s2 - ideal_s2
    
                if delta_s2 > 0.1:
                    flag = "🟥"
                elif delta_s2 > 0.05:
                    flag = "🟨"
                else:
                    flag = "🟩"
    
                print(f"{flag} Spin Contam. : ⟨S²⟩={actual_s2:.4f} (ideal={ideal_s2:.4f}, Δ={delta_s2:.4f})")
    
            except Exception as e:
                print(f"⚠️ Spin Contam. : ⟨S²⟩={summary['spin_contam']:.4f} (ideal=? - error reading multiplicity)")
        else:
            print(f"⚠️ Spin Contam. : ⟨S²⟩={summary['spin_contam']:.4f}")
    
    
    if summary['job_types']:
        print(f" • Job types     : {', '.join(sorted(summary['job_types']))}")
    print()

def run_log_analyzer(logfile=None):
    """
    Wrapper to analyze one or more Gaussian .log files,
    then optionally write CSV(s), with only two prompts total.
    """
    # 1) gather files
    if logfile and logfile.lower() == "all":
        logfiles = [f for f in os.listdir() if f.endswith(".log")]
    elif not logfile:
        ans = prompt("Analyze all .log files in this directory? (y/n): ").strip().lower()
        if ans.startswith('y'):
            logfiles = [f for f in os.listdir() if f.endswith(".log")]
        else:
            compl = PathCompleter(file_filter=lambda f: f.endswith(".log"))
            sel = tab_autocomplete_prompt("Select a .log file to analyze: ", completer=compl).strip()
            logfiles = [sel]
    else:
        logfiles = [logfile]

    if not logfiles:
        print("❌ No .log files found.")
        return

    # 2) CSV export prompt
    save_csv = prompt("Save summary to CSV? (y/n): ").strip().lower().startswith('y')
    if save_csv and len(logfiles) > 1:
        sep_mode = prompt("Separate CSVs per log or one combined file? (separate/combined): ").strip().lower()
        separate = sep_mode.startswith('s')
    else:
        separate = True

    # 3) analyze each
    summaries = []
    for lf in logfiles:
        print(f"\n=== Analyzing {lf} ===")
        analyze_log(lf)
        summaries.append(extract_log_summary(lf))

    # 4) write CSV(s)
    if save_csv:
        if len(logfiles) == 1 or separate:
            for s in summaries:
                csv_name = s['logfile'] + ".summary.csv"
                write_summary_csv(s, csv_name)
                print(f"✅ Wrote {csv_name}")
        else:
            combined_name = "all_logs_summary.csv"
            write_combined_csv(summaries, combined_name)
            print(f"✅ Wrote combined summary: {combined_name}")




def extract_molecule_family(mol_name):
    """
    Extract molecule family from full name.
    
    Examples:
    - L1_Me_CF3_precursor → L1
    - L1_H_H_product → L1
    - benzene_conf1 → benzene
    """
    match = re.match(r'(L\d+)', mol_name)
    if match:
        return match.group(1)
    
    parts = mol_name.split('_')
    if len(parts) >= 2:
        known_types = ['precursor', 'product', 'reactant', 'ts', 'intermediate',
                       'conf', 'conformer', 'isomer', 'cat', 'anion', 'cation']
        if any(t in parts[-1].lower() for t in known_types):
            return '_'.join(parts[:-1])
    
    return parts[0] if parts else mol_name


def extract_pattern_match(mol_name, patterns):
    """
    Check if molecule name matches any of the given patterns.
    
    Parameters
    ----------
    mol_name : str
        Molecule name
    patterns : list of str
        Patterns to match
        
    Returns
    -------
    str
        First matching pattern, or 'other'
    """
    for pattern in patterns:
        if pattern.lower() in mol_name.lower():
            return pattern
    return 'other'


def generate_grouping_key(parsed, modes, patterns=None, ignore_options=None):
    """
    Generate hierarchical grouping key based on multiple modes.
    
    Parameters
    ----------
    parsed : dict
        Parsed filename metadata
    modes : list of str
        Grouping modes to apply (in order)
    patterns : list of str, optional
        Patterns for pattern matching
    ignore_options : set, optional
        Fields to ignore: 'charge', 'multiplicity', 'basis', 'functional'
        
    Returns
    -------
    str
        Composite grouping key
    """
    if ignore_options is None:
        ignore_options = set()
    
    if patterns is None:
        patterns = []
    
    mol = parsed['system_name']
    func = parsed['functional']
    basis = parsed['basis_set']
    charge = parsed.get('charge')
    mult = parsed.get('multiplicity')
    
    # Build key components based on modes
    key_parts = []
    
    for mode in modes:
        mode = mode.strip().lower()
        
        if mode == 'exact':
            # Exact molecule name
            key_parts.append(mol)
        
        elif mode == 'method':
            # Functional and/or basis (respecting ignore options)
            method_parts = []
            if 'functional' not in ignore_options and func:
                method_parts.append(func)
            if 'basis' not in ignore_options and basis:
                method_parts.append(basis)
            if method_parts:
                key_parts.append('_'.join(method_parts))
        
        elif mode == 'family':
            # Molecule family
            family = extract_molecule_family(mol)
            key_parts.append(family)
        
        elif mode == 'pattern':
            # Pattern matching
            if patterns:
                pattern_match = extract_pattern_match(mol, patterns)
                key_parts.append(pattern_match)
        
        elif mode == 'functional':
            # Just functional
            if 'functional' not in ignore_options and func:
                key_parts.append(func)
        
        elif mode == 'basis':
            # Just basis set
            if 'basis' not in ignore_options and basis:
                key_parts.append(basis)
        
        elif mode == 'state':
            # Include charge and multiplicity
            if 'charge' not in ignore_options and charge is not None:
                key_parts.append(f"q{charge}")
            if 'multiplicity' not in ignore_options and mult is not None:
                key_parts.append(f"m{mult}")
    
    # Always add method at the end if not already included
    if 'method' not in modes:
        method_parts = []
        if 'functional' not in ignore_options and func:
            method_parts.append(func)
        if 'basis' not in ignore_options and basis:
            method_parts.append(basis)
        if method_parts:
            key_parts.append('_'.join(method_parts))
    
    # Remove empty parts and join
    key_parts = [p for p in key_parts if p]
    return '_'.join(key_parts) if key_parts else 'ungrouped'


def get_input_directory() -> Optional[str]:
    """
    Use current working directory as input directory.
    
    Returns:
    -------
    str: Current working directory path
    """
    folder = os.getcwd()
    print(f"📁 Using current directory: {folder}")
    
    if not os.path.isdir(folder):
        print("❌ Current directory is invalid.")
        return None
    
    return folder

def parse_log_files(folder: str, log_files: List[str], method: str = 'scf') -> Tuple[List[Dict], List[Tuple]]:
    """
    Parse all log files using FilenameParser and extract energy data.
    
    Parameters:
    ----------
    folder : str
        Directory containing log files
    log_files : list
        List of log file names
    method : str
        Energy extraction method (scf/zpe/mp2/pm2/pmp2/td)
    
    Returns:
    -------
    tuple: (parsed_data, failed_files)
        parsed_data: List of successfully parsed file data
        failed_files: List of (filename, error_message) tuples
    """
    parsed_data = []
    failed_files = []
    
    # Initialize the filename parser
    parser = FilenameParser()
    
    for logfile in log_files:
        filepath = os.path.join(folder, logfile)
        
        try:
            # Parse filename using the existing FilenameParser
            parse_result = parser.parse_filename(logfile)
            
            # Validate parsing (optional - can help identify issues)
            warnings = parser.validate_parse(parse_result, verbose=False)
            
            # Extract energy from the log file using specified method
            energy, energy_type = extract_energy(filepath, method)
            
            if energy is not None:
                # Extract additional data from log file
                log_data = extract_additional_log_data(filepath)
                
                # Combine all data into a single record
                record = {
                    'filename': logfile,
                    'filepath': filepath,
                    'molecule': parse_result['system_name'],
                    'functional': parse_result['functional'],
                    'basis': parse_result['basis_set'],
                    'charge': parse_result['charge'],
                    'multiplicity': parse_result['multiplicity'],
                    'energy': energy,
                    'energy_type': energy_type,
                    'spin_contam': log_data.get('spin_contam'),
                    'parsing_confidence': parse_result['parsing_confidence'],
                    'unparsed_parts': parse_result.get('unparsed_parts', []),
                    'parse_warnings': warnings
                }
                
                parsed_data.append(record)
            else:
                failed_files.append((logfile, f"No {method.upper()} energy found"))
                
        except Exception as e:
            failed_files.append((logfile, str(e)))
    
    return parsed_data, failed_files

# ==============================================================================
# MAIN COMPARISON FUNCTION
# ==============================================================================
def compare_log_energies():
    """
    Main energy comparison function with enhanced Excel output.
    
    This function provides a streamlined workflow for comparing energies across
    multiple Gaussian log files. It generates THREE separate Excel workbooks:
    
    1. All_Data.xlsx - Single sheet with all results
    2. By_System.xlsx - One sheet per molecule/system
    3. By_Functional.xlsx - One sheet per functional
    
    Key Features:
    - Flexible grouping by any combination of: molecule, functional, basis, charge, multiplicity
    - Pattern ignoring using regex (e.g., ignore "product|precursor" variations)
    - Multiple reference energy selection methods
    - Three different Excel organizations for different analysis needs
    - Comprehensive error handling and user feedback
    
    Returns:
    -------
    tuple: (all_results, group_summaries, parsed_data)
        all_results: List of all comparison results
        group_summaries: Dictionary of DataFrames, one per group
        parsed_data: Full parsed data with metadata
    """
    
    print("\n" + "="*80)
    print("📊 ENERGY COMPARISON TOOL - Version 3.0 (Enhanced Excel Output)")
    print("="*80)
    
    # ============================================================================
    # STEP 1: Input Directory Selection
    # ============================================================================
    folder = get_input_directory()
    if not folder:
        return None, None, None
    
    # Find all log files in the directory
    log_files = [f for f in os.listdir(folder) if f.endswith('.log')]
    print(f"\n✅ Found {len(log_files)} log files")
    
    if not log_files:
        print("❌ No log files found in directory.")
        return None, None, None
    
    # ============================================================================
    # STEP 1.5: Energy Method Selection
    # ============================================================================
    method = prompt("Energy method [scf/zpe/mp2/pm2/pmp2/td] (default: scf): ").strip().lower() or "scf"
    if method not in ["scf", "zpe", "mp2", "pm2", "pmp2", "td"]:
        print("⚠️ Unsupported method. Using default SCF.")
        method = "scf"
    
    # ============================================================================
    # STEP 2: Parse Files and Extract Data
    # ============================================================================
    print("\n" + "-"*40)
    print("📖 PARSING LOG FILES")
    print("-"*40)
    
    parsed_data, failed_files = parse_log_files(folder, log_files, method)
    
    # Report parsing results
    print(f"\n✅ Successfully parsed: {len(parsed_data)} files")
    if failed_files:
        print(f"⚠️  Failed to parse: {len(failed_files)} files")
        if len(failed_files) <= 5:
            for file, reason in failed_files:
                print(f"    - {file}: {reason}")
    
    if not parsed_data:
        print("❌ No valid data to compare.")
        return None, None, None
    
    # ============================================================================
    # STEP 3: Configure Grouping Strategy
    # ============================================================================
    print("\n" + "="*80)
    print("🔧 GROUPING CONFIGURATION")
    print("="*80)
    
    group_fields = configure_grouping(parsed_data)
    if not group_fields:
        return None, None, None
    
    # ============================================================================
    # STEP 4: Configure Pattern Ignoring
    # ============================================================================
    print("\n" + "-"*40)
    print("🚫 PATTERN IGNORING")
    print("-"*40)
    
    ignore_patterns = configure_pattern_ignoring(parsed_data, group_fields)
    
    # Apply pattern ignoring to clean up field values
    if ignore_patterns:
        apply_pattern_ignoring(parsed_data, ignore_patterns)
    
    # ============================================================================
    # STEP 5: Create Groups Based on Configuration
    # ============================================================================
    groups = create_groups(parsed_data, group_fields)
    print(f"\n✅ Created {len(groups)} unique groups")
    
    # Filter groups by minimum size
    valid_groups = filter_groups_by_size(groups)
    if not valid_groups:
        return None, None, None
    
    # ============================================================================
    # STEP 6: Select Reference Energy Method
    # ============================================================================
    ref_method = select_reference_method()
    
    # ============================================================================
    # STEP 7: Perform Energy Comparisons
    # ============================================================================
    print("\n" + "="*80)
    print("📊 ENERGY COMPARISONS")
    print("="*80)
    
    all_results, group_summaries, full_parsed_data = perform_comparisons_enhanced(
        valid_groups, group_fields, ref_method
    )
    
    # ============================================================================
    # STEP 8: Save Results (THREE EXCEL WORKBOOKS)
    # ============================================================================
    save_comparison_results_enhanced(all_results, full_parsed_data, ignore_patterns)
    
    # ============================================================================
    # STEP 9: No statistics printing (already shown during comparison)
    # ============================================================================
    print_summary_statistics(group_summaries)
    
    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80)
    
    return all_results, group_summaries, full_parsed_data






def extract_additional_log_data(filepath: str) -> Dict:
    """
    Extract additional data from log file beyond just energy.
    
    Parameters:
    ----------
    filepath : str
        Path to the log file
    
    Returns:
    -------
    dict: Additional extracted data (spin contamination, etc.)
    """
    data = {
        'spin_contam': None,
        'converged': False,
        'num_steps': None
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            # Check for spin contamination
            if '<S**2>' in line:
                match = re.search(r'<S\*\*2>\s*=\s*([\d\.]+)', line)
                if match:
                    data['spin_contam'] = float(match.group(1))
            
            # Check for normal termination
            if 'Normal termination' in line:
                data['converged'] = True
            
            # Count optimization steps
            if 'Step number' in line:
                match = re.search(r'Step number\s+(\d+)', line)
                if match:
                    data['num_steps'] = int(match.group(1))
    
    except Exception as e:
        print(f"    ⚠️  Error extracting additional data from {filepath}: {e}")
    
    return data


def configure_grouping(parsed_data: List[Dict]) -> List[str]:
    """
    Interactive configuration of grouping fields.
    
    Parameters:
    ----------
    parsed_data : list
        List of parsed file data
    
    Returns:
    -------
    list: Selected field names for grouping
    """
    # Determine available fields based on what was successfully parsed
    sample = parsed_data[0]
    available_fields = []
    
    # Check which fields have non-None values
    field_checks = [
        ('molecule', 'Molecule/System name'),
        ('functional', 'Functional/Method'),
        ('basis', 'Basis set'),
        ('charge', 'Charge state'),
        ('multiplicity', 'Spin multiplicity')
    ]
    
    for field, description in field_checks:
        # Check if this field has any non-None values
        if any(record.get(field) is not None for record in parsed_data):
            available_fields.append((field, description))
    
    # Display available fields
    print("\nAvailable fields for grouping:")
    for i, (field, description) in enumerate(available_fields, 1):
        # Show example values for this field
        unique_values = set(str(record.get(field, 'None')) 
                          for record in parsed_data[:5])
        examples = ', '.join(list(unique_values)[:3])
        print(f"  {i}. {field:<15} - {description:<25} (e.g., {examples})")
    
    # Get user selection
    print("\n📋 How do you want to group files for comparison?")
    print("   Enter field numbers (e.g., '1,2,3') or field names")
    print("   Default: molecule,functional,basis")
    
    group_input = input("\nGroup by: ").strip()
    
    # Parse user input
    if not group_input:
        # Use sensible defaults
        group_fields = ['molecule', 'functional', 'basis']
        # Filter to only available fields
        group_fields = [f for f in group_fields 
                       if any(f == af[0] for af in available_fields)]
    else:
        if group_input[0].isdigit():
            # User entered numbers
            indices = [int(x.strip())-1 for x in group_input.split(',')]
            group_fields = [available_fields[i][0] for i in indices 
                          if 0 <= i < len(available_fields)]
        else:
            # User entered field names
            group_fields = [x.strip() for x in group_input.split(',')]
            # Validate against available fields
            valid_fields = [af[0] for af in available_fields]
            group_fields = [f for f in group_fields if f in valid_fields]
    
    if group_fields:
        print(f"\n✅ Grouping by: {', '.join(group_fields)}")
    else:
        print("❌ No valid fields selected")
    
    return group_fields


def configure_pattern_ignoring(parsed_data: List[Dict], 
                               group_fields: List[str]) -> Dict[str, str]:
    """
    Configure regex patterns to ignore in grouping fields.
    Uses a single comma-separated input for all patterns.
    
    Parameters:
    ----------
    parsed_data : list
        List of parsed file data
    group_fields : list
        List of fields being used for grouping
    
    Returns:
    -------
    dict: Field name -> regex pattern to ignore
    """
    print("\nPattern ignoring helps group similar files together.")
    print("Examples:")
    print("  • 'product|precursor' - Groups L1_product and L1_precursor together")
    print("  • '_opt$' - Ignores '_opt' at the end of names")
    print("  • 'Step\\d+' - Ignores Step1, Step2, etc.")
    print("\nEnter patterns to ignore across ALL fields (comma-separated):")
    print("Leave blank to skip pattern ignoring\n")
    
    # Show all unique values for all grouping fields
    print("Current field values:")
    for field in group_fields:
        unique_values = set(str(record.get(field, '')) 
                          for record in parsed_data 
                          if record.get(field) is not None)
        
        if len(unique_values) <= 20:
            examples = sorted(unique_values)[:10]
            print(f"  {field}: {', '.join(examples)}")
            if len(unique_values) > 10:
                print(f"    ... and {len(unique_values) - 10} more")
        else:
            print(f"  {field}: {len(unique_values)} unique values")
    
    # Get patterns from user as comma-separated list
    pattern_input = input("\nIgnore patterns (comma-separated): ").strip()
    
    ignore_patterns = {}
    
    if pattern_input:
        # Split by comma and process each pattern
        patterns = [p.strip() for p in pattern_input.split(',') if p.strip()]
        
        for pattern in patterns:
            # Validate the regex pattern
            try:
                re.compile(pattern)
                # Apply this pattern to ALL grouping fields
                for field in group_fields:
                    # Check if pattern matches any values in this field
                    unique_values = set(str(record.get(field, '')) 
                                      for record in parsed_data 
                                      if record.get(field) is not None)
                    
                    # Only add pattern if it matches something in this field
                    if any(re.search(pattern, val) for val in unique_values):
                        ignore_patterns[field] = pattern
                        print(f"  ✓ Pattern '{pattern}' will be ignored in {field}")
                        break  # Only report once per pattern
            except re.error as e:
                print(f"  ✗ Invalid regex pattern '{pattern}': {e}")
    
    return ignore_patterns



def apply_pattern_ignoring(parsed_data: List[Dict], 
                           ignore_patterns: Dict[str, str]) -> None:
    """
    Apply pattern ignoring to clean up field values in-place.
    
    Parameters:
    ----------
    parsed_data : list
        List of parsed file data (modified in-place)
    ignore_patterns : dict
        Field name -> regex pattern to remove
    """
    if not ignore_patterns:
        return
    
    print("\n🔄 Applying pattern filters...")
    
    for record in parsed_data:
        for field, pattern in ignore_patterns.items():
            if field in record and record[field] is not None:
                original = str(record[field])
                # Apply the regex substitution
                cleaned = re.sub(pattern, '', original)
                # Clean up any resulting issues (double underscores, trailing underscores)
                cleaned = re.sub(r'_+', '_', cleaned)  # Replace multiple _ with single _
                cleaned = cleaned.strip('_').strip()   # Remove leading/trailing _
                
                # Only update if something changed
                if cleaned != original:
                    # Store the original value for reference
                    record[f'{field}_original'] = original
                    record[field] = cleaned
                    # Track that this field was modified
                    if 'modified_fields' not in record:
                        record['modified_fields'] = []
                    record['modified_fields'].append(field)


def create_groups(parsed_data: List[Dict], 
                 group_fields: List[str]) -> Dict[tuple, List[Dict]]:
    """
    Create groups of files based on selected fields.
    
    Parameters:
    ----------
    parsed_data : list
        List of parsed file data
    group_fields : list
        List of field names to use for grouping
    
    Returns:
    -------
    dict: Group key (tuple) -> list of records in that group
    """
    groups = defaultdict(list)
    
    for record in parsed_data:
        # Create group key from selected fields
        # Use 'unknown' for any missing field values
        group_key = tuple(
            record.get(field, 'unknown') if record.get(field) is not None else 'unknown'
            for field in group_fields
        )
        groups[group_key].append(record)
    
    return dict(groups)


def filter_groups_by_size(groups: Dict[tuple, List[Dict]], 
                         min_size: Optional[int] = None) -> Dict[tuple, List[Dict]]:
    """
    Filter groups to only include those with minimum number of files.
    
    Parameters:
    ----------
    groups : dict
        All groups
    min_size : int or None
        Minimum group size (will prompt if None)
    
    Returns:
    -------
    dict: Filtered groups meeting size criterion
    """
    if min_size is None:
        print("\n🔍 FILTER OPTIONS")
        size_input = input("  Minimum files per group for comparison (default: 2): ").strip()
        min_size = int(size_input) if size_input.isdigit() else 2
    
    # Filter groups
    valid_groups = {k: v for k, v in groups.items() if len(v) >= min_size}
    
    print(f"✅ {len(valid_groups)} groups with at least {min_size} files")
    
    if not valid_groups:
        print("❌ No groups meet the minimum size criteria.")
    
    return valid_groups


def select_reference_method() -> str:
    """
    Let user select how to choose reference energy for comparisons.
    
    Returns:
    -------
    str: Reference method choice ('1', '2', or '3')
    """
    print("\n⚡ REFERENCE ENERGY SELECTION")
    print("  1. Lowest energy in group (default)")
    print("  2. Specific charge/multiplicity state")
    print("  3. First file in group")
    print("  4. Neutral singlet if available, else lowest")
    
    ref_method = input("Choose reference method [1-4]: ").strip() or "1"
    
    if ref_method not in ['1', '2', '3', '4']:
        print("  Using default: Lowest energy")
        ref_method = "1"
    
    return ref_method




def select_reference_file(files: List[Dict], ref_method: str, 
                          group_name: str, target_charge: Optional[str] = None,
                          target_mult: Optional[str] = None) -> Optional[Dict]:
    """
    Select the reference file based on the chosen method.
    
    Parameters:
    ----------
    files : list
        List of files in the group (already sorted by energy)
    ref_method : str
        Reference selection method
    group_name : str
        Name of the current group
    target_charge : str or None
        Target charge (for method 2)
    target_mult : str or None
        Target multiplicity (for method 2)
    
    Returns:
    -------
    dict or None: Selected reference file
    """
    if ref_method == "1":
        # Lowest energy (files already sorted)
        return files[0]
    
    elif ref_method == "2":
        # Specific charge/multiplicity
        if target_charge and target_mult:
            for f in files:
                if (str(f.get('charge', '')) == target_charge and 
                    str(f.get('multiplicity', '')) == target_mult):
                    return f
        # Fallback to lowest if not found
        return files[0]
    
    elif ref_method == "3":
        # First file (in original order, not energy order)
        return files[0]
    
    elif ref_method == "4":
        # Neutral singlet if available, else lowest
        for f in files:
            if f.get('charge') == 0 and f.get('multiplicity') == 1:
                return f
        # Fallback to lowest
        return files[0]
    
    # Default fallback
    return files[0]




def save_comparison_results_enhanced(all_results: List[Dict], 
                                     parsed_data: List[Dict],
                                     ignore_patterns: Dict[str, str]) -> None:
    """
    Save comparison results to THREE separate Excel files with different organizations.
    
    Creates:
    1. All_Data.xlsx - Single sheet with all results
    2. By_System.xlsx - One sheet per system (molecule)
    3. By_Functional.xlsx - One sheet per functional
    
    Parameters:
    ----------
    all_results : list
        All comparison results
    parsed_data : list
        Original parsed data with full metadata
    ignore_patterns : dict
        Pattern ignore rules to apply when grouping
    """
    if not all_results:
        print("\n⚠️  No results to save")
        return
    
    print("\n" + "="*80)
    print("💾 SAVE RESULTS")
    print("="*80)
    
    save = input("\nSave results to Excel/CSV? [Y/n]: ").strip().lower()
    
    if save == 'n':
        print("  Results not saved")
        return
    
    # Get base filename
    base_name = input("Output filename base (without extension) [energy_comparison]: ").strip()
    base_name = base_name or "energy_comparison"
    
    print("\n📊 Generating Excel workbooks...")
    
    # Create DataFrames
    df_all = pd.DataFrame(all_results)
    
    # ========================================================================
    # WORKBOOK 1: All Data in Single Sheet
    # ========================================================================
    excel_all = f"{base_name}_All_Data.xlsx"
    try:
        with pd.ExcelWriter(excel_all, engine="xlsxwriter") as writer:
            df_all.to_excel(writer, sheet_name="All_Data", index=False)
            _format_worksheet(writer, "All_Data")
        print(f"✅ Saved: {excel_all}")
    except Exception as e:
        print(f"⚠️  Error saving {excel_all}: {e}")
    
    # ========================================================================
    # WORKBOOK 2: Organized by System (Molecule)
    # ========================================================================
    excel_system = f"{base_name}_By_System.xlsx"
    try:
        system_groups = _organize_by_system(all_results, parsed_data)
        
        with pd.ExcelWriter(excel_system, engine="xlsxwriter") as writer:
            # Create a summary sheet first
            _create_system_summary_sheet(writer, system_groups)
            
            # Create individual sheets for each system
            for system_name, system_data in system_groups.items():
                df_system = pd.DataFrame(system_data)
                # Recalculate ΔE relative to lowest in this system
                df_system = _recalculate_delta_e(df_system)
                
                sheet_name = _sanitize_sheet_name(system_name)
                df_system.to_excel(writer, sheet_name=sheet_name, index=False)
                _format_worksheet(writer, sheet_name, include_system_col=False)
        
        print(f"✅ Saved: {excel_system} ({len(system_groups)} systems)")
    except Exception as e:
        print(f"⚠️  Error saving {excel_system}: {e}")
    
    # ========================================================================
    # WORKBOOK 3: Organized by Functional
    # ========================================================================
    excel_functional = f"{base_name}_By_Functional.xlsx"
    try:
        functional_groups = _organize_by_functional(all_results, parsed_data)
        
        with pd.ExcelWriter(excel_functional, engine="xlsxwriter") as writer:
            # Create a summary sheet first
            _create_functional_summary_sheet(writer, functional_groups)
            
            # Create individual sheets for each functional
            for functional_name, functional_data in functional_groups.items():
                df_functional = pd.DataFrame(functional_data)
                # Recalculate ΔE relative to lowest in this functional
                df_functional = _recalculate_delta_e(df_functional)
                
                sheet_name = _sanitize_sheet_name(functional_name)
                df_functional.to_excel(writer, sheet_name=sheet_name, index=False)
                _format_worksheet(writer, sheet_name, include_functional_col=False)
        
        print(f"✅ Saved: {excel_functional} ({len(functional_groups)} functionals)")
    except Exception as e:
        print(f"⚠️  Error saving {excel_functional}: {e}")
    
    # ========================================================================
    # Also save CSV for compatibility
    # ========================================================================
    csv_file = f"{base_name}_All_Data.csv"
    df_all.to_csv(csv_file, index=False)
    print(f"✅ Saved: {csv_file}")
    
    print("\n" + "="*80)
    print("📁 Output Files Generated:")
    print(f"   1. {excel_all} - All data in one sheet")
    print(f"   2. {excel_system} - Organized by system")
    print(f"   3. {excel_functional} - Organized by functional")
    print(f"   4. {csv_file} - CSV for data processing")
    print("="*80)


def _organize_by_system(all_results: List[Dict], parsed_data: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Organize results by system (molecule), grouping across functionals and basis sets.
    
    Parameters:
    ----------
    all_results : list
        All comparison results
    parsed_data : list
        Original parsed data with molecule information
    
    Returns:
    -------
    dict: System name -> list of results for that system
    """
    # Create a mapping from filename to molecule
    filename_to_molecule = {}
    for record in parsed_data:
        filename_to_molecule[record['filename']] = record.get('molecule', 'Unknown')
    
    # Group results by system
    system_groups = defaultdict(list)
    
    for result in all_results:
        filename = result['Filename']
        system = filename_to_molecule.get(filename, 'Unknown')
        
        # Add system and functional/basis info to result
        enhanced_result = result.copy()
        
        # Extract functional and basis from parsed_data
        for record in parsed_data:
            if record['filename'] == filename:
                enhanced_result['System'] = system
                enhanced_result['Functional'] = record.get('functional', '')
                enhanced_result['Basis'] = record.get('basis', '')
                break
        
        system_groups[system].append(enhanced_result)
    
    return dict(system_groups)


def _organize_by_functional(all_results: List[Dict], parsed_data: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Organize results by functional, grouping across systems and basis sets.
    
    Parameters:
    ----------
    all_results : list
        All comparison results
    parsed_data : list
        Original parsed data with functional information
    
    Returns:
    -------
    dict: Functional name -> list of results for that functional
    """
    # Create a mapping from filename to functional and system
    filename_to_info = {}
    for record in parsed_data:
        filename_to_info[record['filename']] = {
            'functional': record.get('functional', 'Unknown'),
            'molecule': record.get('molecule', 'Unknown'),
            'basis': record.get('basis', 'Unknown')
        }
    
    # Group results by functional
    functional_groups = defaultdict(list)
    
    for result in all_results:
        filename = result['Filename']
        info = filename_to_info.get(filename, {})
        functional = info.get('functional', 'Unknown')
        
        # Add system and basis info to result
        enhanced_result = result.copy()
        enhanced_result['System'] = info.get('molecule', 'Unknown')
        enhanced_result['Functional'] = functional
        enhanced_result['Basis'] = info.get('basis', 'Unknown')
        
        functional_groups[functional].append(enhanced_result)
    
    return dict(functional_groups)


def _recalculate_delta_e(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recalculate ΔE values relative to the lowest energy in the DataFrame.
    
    Parameters:
    ----------
    df : DataFrame
        DataFrame with Energy (Hartree) column
    
    Returns:
    -------
    DataFrame: Updated DataFrame with recalculated ΔE values
    """
    from .utils import hartree_to_ev
    
    if 'Energy (Hartree)' not in df.columns:
        return df
    
    # Find minimum energy
    min_energy = df['Energy (Hartree)'].min()
    
    # Recalculate ΔE
    df['ΔE (Hartree)'] = df['Energy (Hartree)'] - min_energy
    df['ΔE (eV)'] = df['ΔE (Hartree)'].apply(hartree_to_ev)
    
    return df


def _sanitize_sheet_name(name: str) -> str:
    """
    Sanitize sheet name to comply with Excel's requirements.
    
    Excel sheet names must:
    - Be 31 characters or less
    -" Not contain: \ / ? * [ ] :"
    
    Parameters:
    ----------
    name : str
        Original sheet name
    
    Returns:
    -------
    str: Sanitized sheet name
    """
    # Replace invalid characters
    invalid_chars = ['\\', '/', '?', '*', '[', ']', ':']
    for char in invalid_chars:
        name = name.replace(char, '_')
    
    # Truncate if too long
    if len(name) > 31:
        name = name[:28] + "..."
    
    return name


def _create_system_summary_sheet(writer, system_groups: Dict[str, List[Dict]]):
    """
    Create a summary sheet for system-organized workbook.
    
    Parameters:
    ----------
    writer : ExcelWriter
        The Excel writer object
    system_groups : dict
        Dictionary of system groups
    """
    summary_data = []
    
    for system_name, system_data in system_groups.items():
        df = pd.DataFrame(system_data)
        
        summary_data.append({
            'System': system_name,
            'Number of Files': len(system_data),
            'Functionals Used': ', '.join(sorted(set(d.get('Functional', '') for d in system_data))),
            'Basis Sets Used': ', '.join(sorted(set(d.get('Basis', '') for d in system_data))),
            'Energy Range (eV)': df['ΔE (eV)'].max() - df['ΔE (eV)'].min() if 'ΔE (eV)' in df.columns else 0,
            'Min Energy (Hartree)': df['Energy (Hartree)'].min() if 'Energy (Hartree)' in df.columns else 0
        })
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name="Summary", index=False)
    _format_worksheet(writer, "Summary", is_summary=True)


def _create_functional_summary_sheet(writer, functional_groups: Dict[str, List[Dict]]):
    """
    Create a summary sheet for functional-organized workbook.
    
    Parameters:
    ----------
    writer : ExcelWriter
        The Excel writer object
    functional_groups : dict
        Dictionary of functional groups
    """
    summary_data = []
    
    for functional_name, functional_data in functional_groups.items():
        df = pd.DataFrame(functional_data)
        
        summary_data.append({
            'Functional': functional_name,
            'Number of Files': len(functional_data),
            'Systems Calculated': ', '.join(sorted(set(d.get('System', '') for d in functional_data))),
            'Basis Sets Used': ', '.join(sorted(set(d.get('Basis', '') for d in functional_data))),
            'Energy Range (eV)': df['ΔE (eV)'].max() - df['ΔE (eV)'].min() if 'ΔE (eV)' in df.columns else 0,
            'Min Energy (Hartree)': df['Energy (Hartree)'].min() if 'Energy (Hartree)' in df.columns else 0
        })
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name="Summary", index=False)
    _format_worksheet(writer, "Summary", is_summary=True)


def _format_worksheet(writer, sheet_name: str, 
                     include_system_col: bool = True,
                     include_functional_col: bool = True,
                     is_summary: bool = False):
    """
    Apply formatting to an Excel worksheet.
    
    Parameters:
    ----------
    writer : ExcelWriter
        The Excel writer object
    sheet_name : str
        Name of the sheet to format
    include_system_col : bool
        Whether to include system column in formatting
    include_functional_col : bool
        Whether to include functional column in formatting
    is_summary : bool
        Whether this is a summary sheet (different formatting)
    """
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    
    # Create formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D3D3D3',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    number_format = workbook.add_format({'num_format': '0.0000'})
    energy_format = workbook.add_format({'num_format': '0.000000'})
    
    # Set header format
    worksheet.set_row(0, None, header_format)
    
    if is_summary:
        # Summary sheet formatting
        worksheet.set_column('A:A', 30)  # System/Functional name
        worksheet.set_column('B:B', 15)  # Number of Files
        worksheet.set_column('C:D', 40)  # Lists of methods/basis
        worksheet.set_column('E:E', 18, number_format)  # Energy Range
        worksheet.set_column('F:F', 20, energy_format)  # Min Energy
    else:
        # Data sheet formatting
        col = 0
        
        # Filename
        worksheet.set_column(col, col, 50)
        col += 1
        
        # System (if included)
        if include_system_col:
            worksheet.set_column(col, col, 20)
            col += 1
        
        # Functional (if included)
        if include_functional_col:
            worksheet.set_column(col, col, 15)
            col += 1
        
        # Basis
        worksheet.set_column(col, col, 15)
        col += 1
        
        # Charge, Mult
        worksheet.set_column(col, col + 1, 8)
        col += 2
        
        # Energy (Hartree)
        worksheet.set_column(col, col, 18, energy_format)
        col += 1
        
        # ΔE (Hartree)
        worksheet.set_column(col, col, 15, energy_format)
        col += 1
        
        # ΔE (eV)
        worksheet.set_column(col, col, 12, number_format)
        col += 1
        
        # ⟨S²⟩
        worksheet.set_column(col, col, 10, number_format)


def perform_comparisons_enhanced(valid_groups: Dict[tuple, List[Dict]], 
                                 group_fields: List[str],
                                 ref_method: str):
    """
    Enhanced version that returns both results and parsed_data for use in save function.
    
    Parameters:
    ----------
    valid_groups : dict
        Groups to compare
    group_fields : list
        Fields used for grouping
    ref_method : str
        Reference selection method
    
    Returns:
    -------
    tuple: (all_results, group_summaries, all_parsed_data)
    """
    from .utils import hartree_to_ev
    
    all_results = []
    group_summaries = {}
    all_parsed_data = []
    
    # If method 2, get target charge/mult once
    if ref_method == "2":
        target_charge = input("  Target charge for all groups: ").strip()
        target_mult = input("  Target multiplicity for all groups: ").strip()
    
    for group_idx, (group_key, files) in enumerate(valid_groups.items(), 1):
        # Create readable group name
        group_name = "_".join(str(v) for v in group_key)
        
        print(f"\n{'='*60}")
        print(f"📂 Group {group_idx}/{len(valid_groups)}: {group_name}")
        print(f"   {len(files)} files in this group")
        
        # Sort files by energy for consistent ordering
        files.sort(key=lambda x: x['energy'])
        
        # Store all parsed data
        all_parsed_data.extend(files)
        
        # Determine reference based on selected method
        reference = select_reference_file(files, ref_method, group_name,
                                        locals().get('target_charge'),
                                        locals().get('target_mult'))
        
        if not reference:
            print("   ⚠️  Could not determine reference, using lowest energy")
            reference = files[0]
        
        ref_energy = reference['energy']
        group_data = []
        
        # Display header
        print(f"   Reference: {reference['filename']}")
        print(f"   {'File':<45} {'Chg':>4} {'Mult':>4} {'ΔE (eV)':>10} {'⟨S²⟩':>8}")
        print("   " + "-"*75)
        
        # Calculate relative energies for each file
        for file_data in files:
            # Calculate energy difference
            delta_hartree = file_data['energy'] - ref_energy
            delta_ev = hartree_to_ev(delta_hartree)
            
            # Prepare result record - essential columns only
            result = {
                'Filename': file_data['filename'],
                'Charge': file_data.get('charge', ''),
                'Multiplicity': file_data.get('multiplicity', ''),
                'Energy (Hartree)': file_data['energy'],
                'ΔE (Hartree)': delta_hartree,
                'ΔE (eV)': delta_ev,
                '⟨S²⟩': file_data.get('spin_contam', ''),
            }
            
            group_data.append(result)
            all_results.append(result)
            
            # Display summary line
            fname_short = file_data['filename'][:45]
            charge = str(file_data.get('charge', '?'))
            mult = str(file_data.get('multiplicity', '?'))
            s2_val = file_data.get('spin_contam')
            s2_str = f"{s2_val:.4f}" if s2_val is not None else "N/A"
            
            # Mark reference with a special indicator
            marker = "📍" if file_data == reference else "  "
            print(f"   {marker} {fname_short:<43} {charge:>4} {mult:>4} {delta_ev:>10.4f} {s2_str:>8}")
        
        # Store group summary as DataFrame
        group_summaries[group_name] = pd.DataFrame(group_data)
    
    return all_results, group_summaries, all_parsed_data


def select_reference_file(files: List[Dict], ref_method: str, 
                          group_name: str, target_charge=None,
                          target_mult=None):
    """
    Select the reference file based on the chosen method.
    """
    if ref_method == "1":
        return files[0]
    elif ref_method == "2":
        if target_charge and target_mult:
            for f in files:
                if (str(f.get('charge', '')) == target_charge and 
                    str(f.get('multiplicity', '')) == target_mult):
                    return f
        return files[0]
    elif ref_method == "3":
        return files[0]
    elif ref_method == "4":
        for f in files:
            if f.get('charge') == 0 and f.get('multiplicity') == 1:
                return f
        return files[0]
    return files[0]






def print_summary_statistics(group_summaries: Dict[str, pd.DataFrame]) -> None:
    """
    Print summary statistics for each group.
    Modified to not print anything after Excel is saved.
    
    Parameters:
    ----------
    group_summaries : dict
        DataFrames for each group
    """
    # Do nothing - statistics already shown during comparison
    pass





def analyze_zmatrix_scan_logs():
    """
    Analyze Gaussian log files from Z-matrix scan.
    - Extracts SCF or chosen energy method
    - Pulls scan variables from associated .com files
    - Verifies normal termination
    - Saves summary CSV, Excel
    - Plots ΔE vs step and optional 2D heatmap
    """

    scan_dir = prompt("Enter scan folder name (e.g., scan1_scan_inputs): ",
                      completer=MultiPathCompleter()).strip()
    if not os.path.isdir(scan_dir):
        print("❌ Folder not found.")
        return

    method = prompt("Energy method [scf/zpe/mp2/pm2/pmp2/td] (default: scf): ").strip().lower() or "scf"
    if method not in ["scf", "zpe", "mp2", "pm2", "pmp2", "td"]:
        print("⚠️ Unsupported method. Using default SCF.")
        method = "scf"

    log_files = sorted(f for f in os.listdir(scan_dir) if f.endswith(".log"))
    if not log_files:
        print("❌ No log files found.")
        return

    records = []
    skipped = []

    for log in log_files:
        log_path = os.path.join(scan_dir, log)
        com_path = log_path.replace(".log", ".com")

        if not is_gaussian_terminated(log_path):
            skipped.append((log, "Not normally terminated"))
            continue

        energy, _ = extract_energy(log_path, method)
        if energy is None:
            skipped.append((log, "Energy extraction failed"))
            continue

        var_values = extract_scan_variables_from_com(com_path)
        records.append({
            "LogFile": log,
            "Energy (Hartree)": energy,
            **var_values
        })

    if not records:
        print("❌ No valid logs parsed.")
        return

    df = pd.DataFrame(records)
    ref_energy = df["Energy (Hartree)"].min()
    df["ΔE (eV)"] = df["Energy (Hartree)"].apply(lambda x: hartree_to_ev(x - ref_energy))

    # Sort and export
    scan_name = os.path.basename(scan_dir.rstrip("/"))
    var_cols = [col for col in df.columns if col not in ["LogFile", "Energy (Hartree)", "ΔE (eV)"]]
    df.sort_values(by=var_cols, inplace=True)

    out_csv = os.path.join(scan_dir, f"{scan_name}_scan_summary.csv")
    out_xlsx = os.path.join(scan_dir, f"{scan_name}_scan_summary.xlsx")
    df.to_csv(out_csv, index=False)
    df.to_excel(out_xlsx, index=False)

    print(f"\n✅ Scan analysis saved to:\n- {out_csv}\n- {out_xlsx}")

    # === Plot ΔE vs step index ===
    plt.figure()
    plt.plot(range(1, len(df) + 1), df["ΔE (eV)"], marker='o')
    plt.xlabel("Step Index")
    plt.ylabel("ΔE (eV)")
    plt.title("ΔE vs Step Index")
    plt.grid(True)
    step_plot = os.path.join(scan_dir, f"{scan_name}_deltaE_vs_step.png")
    plt.savefig(step_plot, dpi=300)
    plt.close()
    print(f"📈 Step plot saved to {step_plot}")

    # === If 1 variable, also plot ΔE vs that variable ===
    if len(var_cols) == 1:
        vcol = var_cols[0]
        plt.figure()
        plt.plot(df[vcol], df["ΔE (eV)"], marker='o')
        plt.xlabel(vcol)
        plt.ylabel("ΔE (eV)")
        plt.title(f"Energy Scan vs {vcol}")
        plt.grid(True)
        out_plot = os.path.join(scan_dir, f"{scan_name}_plot.png")
        plt.savefig(out_plot, dpi=300)
        plt.close()
        print(f"📈 1D Plot saved to {out_plot}")

    # === Optional heatmap if 2D ===
    if len(var_cols) == 2:
        xvar, yvar = var_cols
        pivot = df.pivot(index=yvar, columns=xvar, values="ΔE (eV)")
        plt.figure(figsize=(6, 5))
        c = plt.pcolor(pivot.columns, pivot.index, pivot.values, shading='auto', cmap='viridis')
        plt.colorbar(c, label="ΔE (eV)")
        plt.xlabel(xvar)
        plt.ylabel(yvar)
        plt.title("Heatmap of ΔE (eV)")
        plt.tight_layout()
        heatmap_file = os.path.join(scan_dir, f"{scan_name}_heatmap.png")
        plt.savefig(heatmap_file, dpi=300)
        plt.close()
        print(f"📊 Heatmap saved to {heatmap_file}")

    # === Skipped logs ===
    if skipped:
        print(f"\n⚠️ Skipped {len(skipped)} file(s):")
        for log, reason in skipped:
            print(f" - {log}: {reason}")



