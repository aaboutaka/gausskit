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



def compare_log_energies():
    import os
    import matplotlib.pyplot as plt
    from collections import defaultdict
    from prompt_toolkit import prompt
    from .utils import is_gaussian_terminated, extract_energy, hartree_to_ev

    try:
        import pandas as pd
        has_pandas = True
        try:
            import xlsxwriter
            has_xlsx = True
        except ImportError:
            has_xlsx = False
    except ImportError:
        has_pandas = False
        has_xlsx = False
    

    def plot_group(group, group_data):
        labels = [os.path.basename(d['Filename']) for d in group_data]
        values = [d['ΔE (eV)'] for d in group_data]
        plt.figure(figsize=(max(6, len(labels)*0.8), 4))
        bars = plt.bar(labels, values)
        plt.ylabel("ΔE (eV)")
        plt.title(f"ΔE for {group}")
        plt.xticks(rotation=45, ha='right')
        for b, v in zip(bars, values):
            plt.text(b.get_x() + b.get_width()/2, v, f"{v:.2f}", ha='center', va='bottom', fontsize=8)
        plt.tight_layout()
        plt.savefig(f"deltaE_{group}.png", dpi=300)
        plt.close()

    print("=" * 70)
    print("Advanced Energy Comparison: Grouped by Functional+Basis or Molecule")
    print("=" * 70)

    method = prompt("Energy method [scf/zpe/mp2/pm2/pmp2/td] (default: scf): ").strip().lower()
    if method not in ["scf", "zpe", "mp2", "pm2", "pmp2", "td"]:
        method = "scf"
    
    exclude = prompt("Exclude files with substring? (press ENTER to skip): ").strip()
    exclude = exclude if exclude else None
    
    mol_filter = prompt("Filter by molecule name (e.g. H2 or H2O)? (default: all): ").strip()
    mol_filter = mol_filter if mol_filter else None
    
    comparison_mode = prompt("Comparison mode: [1] Same method (default)  [2] Same geometry  [3] Both: ").strip()
    comparison_mode = comparison_mode if comparison_mode in ["1", "2", "3"] else "1"


    save_prompt = prompt("Save results to CSV/Excel? (y/n) (default: y): ").strip().lower()
    save_results = has_pandas and (save_prompt in ["", "y", "yes"])
    
    sheet_mode = "group"
    if save_results:
        sheet_mode_prompt = prompt("Excel sheet mode: [1] Group (default)  [2] Molecule: ").strip()
        sheet_mode = "molecule" if sheet_mode_prompt == "2" else "group"
     

    log_files = [f for f in os.listdir(".") if f.endswith(".log") and (exclude not in f if exclude else True)]
    if mol_filter:
        log_files = [f for f in log_files if f.startswith(mol_filter + "_")]

    data = []
    group_dict = defaultdict(list)
    skipped_logs = []

    for log in log_files:
        ok, err = is_gaussian_terminated(log)
        if not ok:
            skipped_logs.append((log, err))
            continue
        energy, extras = extract_energy(log, method)
        if energy is None:
            skipped_logs.append((log, "Energy extraction failed"))
            continue

        base = log[:-4]
        parts = base.split("_")
        if len(parts) < 3:
            skipped_logs.append((log, "Invalid filename format"))
            continue

        mol = parts[0]
        func = parts[-2]
        basis = parts[-1]
        
        groups = []
        if comparison_mode in ["1", "3"]:
            groups.append(f"{func}_{basis}")
        if comparison_mode in ["2", "3"]:
            groups.append(mol)

        from .analyze import extract_log_summary  # add this at the top of the function

        summary = extract_log_summary(log)
        spin_s2 = summary.get("spin_contam")
        multiplicity = summary.get("multiplicity")
        ideal_s2 = None
        delta_s2 = None
        if spin_s2 is not None and multiplicity is not None:
            ideal_s2 = ((multiplicity - 1) * (multiplicity + 1)) / 4
            delta_s2 = spin_s2 - ideal_s2


        
        record = {
            "Filename": log,
            "Molecule": mol,
            "Functional": func,
            "BasisSet": basis,
            "Group": groups[0] if groups else "Unknown",
            "Energy (Hartree)": energy,
            "Extras": extras,
            "⟨S²⟩": spin_s2,
            "⟨S²⟩ Ideal": ideal_s2,
            "Δ⟨S²⟩": delta_s2
        }
        data.append(record)
        for g in groups:
            group_dict[g].append(record)


    if not data:
        print("❌ No valid log files or energies found.")
        return

    all_rows = []
    excel_sheets = {}

    all_rows = []
    excel_sheets = {}

    for group, entries in group_dict.items():
        entries.sort(key=lambda r: r["Energy (Hartree)"])
        ref = entries[0]
        ref_energy = ref["Energy (Hartree)"]

        print(f"\n📊 Group: {group} — {len(entries)} entries")
        print(f"{'Filename':<40} {'ΔE (Ha)':>12} {'ΔE (eV)':>10}")

        group_data = []
        for rec in entries:
            delta_h = rec["Energy (Hartree)"] - ref_energy
            delta_ev = hartree_to_ev(delta_h)

            # S² values
            s2_rec = rec.get("⟨S²⟩")
            s2_ideal_rec = rec.get("⟨S²⟩ Ideal")
            s2_ref = ref.get("⟨S²⟩")
            s2_ideal_ref = ref.get("⟨S²⟩ Ideal")
            delta_s2_rec = s2_rec - s2_ideal_rec if s2_rec is not None and s2_ideal_rec is not None else None
            delta_s2_ref = s2_ref - s2_ideal_ref if s2_ref is not None and s2_ideal_ref is not None else None

            row = {
                "Filename": rec["Filename"],
                "Reference": ref["Filename"],
                "Molecule": rec["Molecule"],
                "Functional": rec["Functional"],
                "BasisSet": rec["BasisSet"],
                "Energy (Hartree)": rec["Energy (Hartree)"],
                "ΔE (Hartree)": delta_h,
                "ΔE (eV)": delta_ev,
                "⟨S²⟩ (This)": s2_rec,
                "⟨S²⟩ Ideal (This)": s2_ideal_rec,
                "Δ⟨S²⟩ (This)": delta_s2_rec,
                "⟨S²⟩ (Ref)": s2_ref,
                "⟨S²⟩ Ideal (Ref)": s2_ideal_ref,
                "Δ⟨S²⟩ (Ref)": delta_s2_ref
            }

            group_data.append(row)
            all_rows.append(row)

            print(f"{rec['Filename']:<30} vs {ref['Filename']:<30}")
            print(f"  ΔE: {delta_h:>10.6f} Ha = {delta_ev:>8.4f} eV")
            print(f"  ⟨S²⟩ (This) : {s2_rec:.4f}   Ideal: {s2_ideal_rec:.4f}   Δ: {delta_s2_rec:.4f}" if s2_rec is not None else "  ⟨S²⟩ (This) : N/A")
            print(f"  ⟨S²⟩ (Ref)  : {s2_ref:.4f}   Ideal: {s2_ideal_ref:.4f}   Δ: {delta_s2_ref:.4f}" if s2_ref is not None else "  ⟨S²⟩ (Ref)  : N/A")
            print("-" * 80)
            
        plot_group(group, group_data)
        if save_results:
            df_group = pd.DataFrame(group_data)
            excel_sheets[group] = df_group

    if save_results:
        if all_rows:
            df_all = pd.DataFrame(all_rows)
            if "Group" in df_all.columns and "ΔE (eV)" in df_all.columns:
                df_all.sort_values(by=["Group", "ΔE (eV)"], inplace=True)
            excel_sheets["Global"] = df_all
            base = f"benchmark_energy_{method}"
            if not has_xlsx:
                print("❌ Missing required module 'xlsxwriter'. Install it via:")
                print("   pip install XlsxWriter")
                print("Exiting without saving Excel files.")
                return
            with pd.ExcelWriter(base + ".xlsx", engine="xlsxwriter") as writer:
                if sheet_mode == "group":
                    for sheet, df in excel_sheets.items():
                        df.to_excel(writer, sheet_name=sheet[:31], index=False)
                elif sheet_mode == "molecule":
                    mol_groups = df_all.groupby("Molecule")
                    for mol, dfmol in mol_groups:
                        dfmol.to_excel(writer, sheet_name=mol[:31], index=False)
            
            df_all.to_csv(base + ".csv", index=False)
            print(f"\n✅ Saved: {base}.xlsx and {base}.csv")
        else:
            print("⚠️ No valid energy records to save.")

    if skipped_logs:
        with open("skipped_logs_summary.txt", "w") as f:
            for log, reason in skipped_logs:
                f.write(f"{log}: {reason}\n")
        print(f"⚠️ Skipped {len(skipped_logs)} files. See 'skipped_logs_summary.txt'.")
 


