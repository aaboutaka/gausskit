import os
import re
import csv
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter
from gausskit.completions import tab_autocomplete_prompt

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
        if '<S**2>' in line:
            sm = re.search(r'<S\*\*2>\s*=\s*([\d\.]+)', line)
            if sm:
                summary['spin_contam'] = float(sm.group(1))

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

