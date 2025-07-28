#!/usr/bin/env python3
import os
import re
import csv
import numpy as np
import matplotlib.pyplot as plt

from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter

# ── Helpers ────────────────────────────────────────────────────────────────────

def _xlabel(axis):
    """
    Turn axis code ('cm','nm','ev') into the matching axis label.
    """
    return {
        'cm': "Wavenumber (cm⁻¹)",
        'nm': "Wavelength (nm)",
        'ev': "Energy (eV)",
    }[axis]


def convert_axis(x_arr, axis):
    """Convert wavenumbers (cm⁻¹) into nm or eV if requested."""
    if axis == 'nm':
        return 1e7 / x_arr, "Wavelength (nm)"
    elif axis == 'ev':
        return x_arr / 8065.54429, "Energy (eV)"
    else:
        return x_arr, "Wavenumber (cm⁻¹)"

# ── Parsing functions ──────────────────────────────────────────────────────────

def parse_spectrum(logfile, shift=0.0, normalize=False):
    """
    Extract (ν_cm, I) arrays from the 'Final Spectrum' block of a .log.
    Applies an energy shift and optional normalization.
    """
    with open(logfile, errors='ignore') as f:
        lines = f.read().splitlines()
    # find the Final Spectrum marker
    try:
        start = next(i for i, L in enumerate(lines) if "Final Spectrum" in L) + 1
    except StopIteration:
        raise ValueError(f"No 'Final Spectrum' in {logfile!r}")

    pat = re.compile(r'^\s*([-+]?\d*\.\d+)\s+([-\d\.DE+]+)')
    nu, I = [], []
    for L in lines[start:]:
        m = pat.match(L)
        if not m:
            if nu:
                break
            continue
        val = float(m.group(1)) + shift
        raw = m.group(2).replace('D','E')
        try:
            inten = float(raw)
        except ValueError:
            print(f"⚠️ Could not parse intensity '{raw}' in {logfile}; setting to 0")
            inten = 0.0
        nu.append(val)
        I.append(inten)

    if not nu:
        raise ValueError(f"No stick data parsed from {logfile!r}")

    nu = np.array(nu)
    I  = np.array(I)
    if normalize and I.max() > 0:
        I = I / I.max()
    return nu, I

def parse_exp_data(path, input_unit='ev', normalize=False, mode='1'):
    """
    Read an experimental CSV with columns [x, I1, I2].
    Skip negative x, convert to cm⁻¹, pick column(s) per mode.
    mode: '1'→I1, '2'→I2, '3'→(I1+I2)/2, '4'→both.
    Returns (ν_cm, I1, I2_or_None).
    """
    x_list, y1_list, y2_list = [], [], []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        next(reader, None)
        for i, row in enumerate(reader, 2):
            try:
                x = float(row[0])
                if x < 0:
                    continue
                if input_unit == 'nm':
                    x = 1e7 / x
                elif input_unit == 'ev':
                    x = x * 8065.54429

                y1 = float(row[1])
                y2 = float(row[2]) if len(row) > 2 and row[2].strip() else 0.0

                if mode == '1':
                    x_list.append(x); y1_list.append(y1)
                elif mode == '2':
                    x_list.append(x); y1_list.append(y2)
                elif mode == '3':
                    x_list.append(x); y1_list.append((y1+y2)/2)
                else:  # '4'
                    x_list.append(x); y1_list.append(y1); y2_list.append(y2)
            except Exception as e:
                print(f"⚠️ Skipping line {i} in {path}: {row} ({e})")

    nu = np.array(x_list)
    I1 = np.array(y1_list)
    I2 = np.array(y2_list) if mode == '4' else None

    if normalize and I1.size and I1.max() > 0:
        I1 = I1 / I1.max()
        if I2 is not None and I2.max() > 0:
            I2 = I2 / I2.max()

    return nu, I1, I2

# ── Plotting routines ─────────────────────────────────────────────────────────

def plot_log_spectra(logs, broad, normalize, shift, axis,
                     overlay_sticks, csv_out, png_out,
                     auto_xlim=False, xlim=None):
    all_x, all_y = [], []
    plt.figure()
    xlabel = None

    for log in logs:
        nu, I = parse_spectrum(log, shift, normalize)
        base = os.path.splitext(os.path.basename(log))[0]

        # export CSV?
        if csv_out:
            fn = f"{base}_spectrum.csv"
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow([ "Energy_cm^-1", "Intensity" ])
                for x,i in zip(nu, I):
                    w.writerow([ f"{x:.6f}", f"{i:.6e}" ])
            print(f"🔖 Wrote CSV: {fn}")

        if broad is not None:
            grid = np.linspace(nu.min(), nu.max(), 2000)
            sigma = broad / (2*np.sqrt(2*np.log(2)))
            prof  = sum(i*np.exp(-0.5*((grid - x)/sigma)**2)
                        for x,i in zip(nu, I))
            xplt, xlabel = convert_axis(grid, axis)
            plt.plot(xplt, prof, label=base)
            all_x.append(xplt); all_y.append(prof)

            if overlay_sticks:
                sx, _ = convert_axis(nu, axis)
                plt.vlines(sx, 0, I, linestyles='dashed')
                all_x.append(sx); all_y.append(I)

        else:
            sx, xlabel = convert_axis(nu, axis)
            idx = np.argsort(sx)
            yv = I[idx]
            plt.vlines(sx[idx], 0, yv, linestyles='solid')
            all_x.append(sx[idx]); all_y.append(yv)

    plt.xlabel(xlabel)
    plt.ylabel("Intensity (arb.)")
    plt.legend()
    plt.tight_layout()

    # auto-trim
    if auto_xlim and all_x and all_y:
        X = np.concatenate(all_x); Y = np.concatenate(all_y)
        thr = Y.max() * (0.001 if broad is not None else 0.0)
        mask = Y > thr
        if mask.any():
            mn, mx = X[mask].min(), X[mask].max()
            pad = 0.05 * (mx - mn)
            plt.xlim(mn - pad, mx + pad)

    if xlim is not None:
        plt.xlim(xlim)

    if png_out:
        if logs:
            if len(logs) == 1:
                base = os.path.splitext(os.path.basename(logs[0]))[0]
                outname = f"{base}.png"
            else:
                outname = "Combined_Logs.png"
        else:
            outname = png_out  # fallback

        plt.savefig(outname, dpi=300)
        plt.close()
        print(f"🖼️    Wrote PNG: {outname}")
    else:
        plt.show()

def plot_exp_spectra(exps, input_unit, axis,
                     normalize, mode, csv_out, png_out,
                     auto_xlim=False, xlim=None):
    all_x, all_y = [], []
    plt.figure()
    xlabel = None

    for path in exps:
        if not os.path.exists(path):
            print(f"❌ CSV not found: {path}")
            continue
        base = os.path.splitext(os.path.basename(path))[0]
        nu_cm, I1, I2 = parse_exp_data(path, input_unit, normalize, mode)
        xplt, xlabel = convert_axis(nu_cm, axis)

        # CSV of converted data?
        if csv_out:
            fn = f"{base}_exp_{axis}.csv"
            with open(fn, 'w', newline='') as f:
                w = csv.writer(f)
                hdr = [xlabel, "I1"]
                if I2 is not None: hdr.append("I2")
                w.writerow(hdr)
                for i,x in enumerate(xplt):
                    row = [ f"{x:.6f}", f"{I1[i]:.6e}" ]
                    if I2 is not None:
                        row.append(f"{I2[i]:.6e}")
                    w.writerow(row)
            print(f"🔖 Wrote CSV: {fn}")

        if mode == '4' and I2 is not None:
            plt.plot(xplt, I1, '--', label=f"{base} (col2)")
            plt.plot(xplt, I2, '-.', label=f"{base} (col3)")
            all_x.extend([xplt,xplt]); all_y.extend([I1,I2])
        else:
            plt.plot(xplt, I1, '-', label=base)
            all_x.append(xplt); all_y.append(I1)

    plt.xlabel(xlabel)
    plt.ylabel("Normalized Intensity" if normalize else "Intensity")
    plt.legend()
    plt.tight_layout()

    if auto_xlim and all_x and all_y:
        X = np.concatenate(all_x); Y = np.concatenate(all_y)
        mask = Y > 0
        if mask.any():
            mn, mx = X[mask].min(), X[mask].max()
            pad = 0.05*(mx-mn)
            plt.xlim(mn - pad, mx + pad)

    if xlim is not None:
        plt.xlim(xlim)

    if png_out:
        plt.savefig(png_out, dpi=300)
        print(f"🖼️  Wrote PNG: {png_out}")
    else:
        plt.show()

def plot_combined(logs, exps, broad, normalize_log, shift, axis,
                  overlay_sticks, normalize_exp, mode, csv_out, png_out,
                  auto_xlim=False, xlim=None):
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    all_x = np.empty(0); all_y = np.empty(0)
    plt.figure()
    xlabel = _xlabel(axis)

    # logs first
    for i, log in enumerate(logs):
        nu, I = parse_spectrum(log, shift, normalize_log)
        base = os.path.splitext(os.path.basename(log))[0]
        c = colors[i % len(colors)]

        if broad is not None:
            grid = np.linspace(nu.min(), nu.max(), 2000)
            sigma = broad / (2*np.sqrt(2*np.log(2)))
            prof  = sum(i_val*np.exp(-0.5*((grid - nu_val)/sigma)**2)
                        for nu_val,i_val in zip(nu,I))
            xplt, _ = convert_axis(grid, axis)
            plt.plot(xplt, prof, color=c, label=base)
            all_x = np.concatenate((all_x, xplt))
            all_y = np.concatenate((all_y, prof))
            if overlay_sticks:
                sx,_ = convert_axis(nu, axis)
                plt.vlines(sx, 0, I, color=c, alpha=0.6)
        else:
            sx,_ = convert_axis(nu, axis)
            idx = np.argsort(sx)
            xv, yv = sx[idx], I[idx]
            plt.vlines(xv, 0, yv, color=c)
            all_x = np.concatenate((all_x, xv))
            all_y = np.concatenate((all_y, yv))

    # then experimental
    offset = len(logs)
    for j, path in enumerate(exps):
        if not os.path.exists(path):
            print(f"❌ CSV not found: {path}")
            continue
        c1 = colors[(offset + j*2) % len(colors)]
        nu_cm, I1, I2 = parse_exp_data(path, axis, normalize_exp, mode)
        xplt, _ = convert_axis(nu_cm, axis)
        base = os.path.splitext(os.path.basename(path))[0]

        if mode=='4' and I2 is not None:
            plt.plot(xplt, I1, '--', color=c1, label=f"{base} (col2)")
            plt.plot(xplt, I2, '-.', color=colors[(offset+j*2+1)%len(colors)], label=f"{base} (col3)")
            all_x = np.concatenate((all_x, xplt, xplt))
            all_y = np.concatenate((all_y, I1, I2))
        else:
            sty = '--' if mode=='2' else '-'
            plt.plot(xplt, I1, sty, color=c1, label=base)
            all_x = np.concatenate((all_x, xplt))
            all_y = np.concatenate((all_y, I1))

    plt.xlabel(xlabel)
    plt.ylabel("Intensity (arb.)")
    plt.legend()
    plt.tight_layout()

    if auto_xlim and all_x.size and all_y.size:
        thr = all_y.max() * (0.001 if broad is not None else 0.0)
        mask = all_y > thr
        if mask.any():
            mn, mx = all_x[mask].min(), all_x[mask].max()
            pad = 0.05*(mx-mn)
            plt.xlim(mn - pad, mx + pad)

    if xlim is not None:
        plt.xlim(xlim)

    if png_out:
        if logs:
            if len(logs) == 1:
                base = os.path.splitext(os.path.basename(logs[0]))[0]
                if exps:
                    outname = f"{base}_Exp.png"
                else:
                    outname = f"{base}.png"
            else:
                outname = "Combined_Logs.png" if not exps else "Combined_Logs_Exp.png"
        elif exps:
            outname = "Only_Exp.png"
        else:
            outname = png_out  # fallback

        plt.savefig(outname, dpi=300)
        plt.close()
        print(f"🖼️   Wrote PNG: {outname}")
    else:
        plt.show()

#    if png_out:
#        # if exactly one log + some CSVs, name <log>_Exp.png
#        if len(logs)==1 and exps:
#            base = os.path.splitext(os.path.basename(logs[0]))[0]
#            outname = f"{base}_Exp.png"
#        else:
#            outname = png_out
#        plt.savefig(outname, dpi=300)
#        plt.close()
#        print(f"🖼️  Wrote PNG: {outname}")
#    else:
#        plt.show()

# ── Interactive main ───────────────────────────────────────────────────────────

def main():
    print("="*60)
    print("      Vibronic Spectrum Tool")
    print("="*60)

    mode = prompt("[1] Log-only  [2] Exp-only  [3] Combined (default=3): ").strip() or "3"
    ax   = prompt("X-axis units: [1] cm⁻¹  [2] nm  [3] eV (default=3): ").strip() or "3"
    axis = 'cm' if ax=='1' else 'nm' if ax=='2' else 'ev'

    if mode == '1':
        raw = prompt("Log files (comma-sep): ",
                     completer=PathCompleter(file_filter=lambda f:f.endswith('.log'))).strip()
        logs = [s.strip() for s in raw.split(',') if s.strip()]
        # filter invalid
        valid, bad = [], []
        for f in logs:
            if not os.path.exists(f) or "Final Spectrum" not in open(f, errors='ignore').read():
                bad.append(f)
            else:
                valid.append(f)
        if bad:
            print(f"⚠️ Skipping {len(bad)} bad logs: {', '.join(bad)}")
        if not valid:
            print("❌ No valid FC logs."); return
        bf    = prompt("Broadening FWHM (cm⁻¹) [ENTER=stick only]: ").strip()
        broad = float(bf) if bf else None
        norm  = prompt("Normalize? (y/n) [default=y]: ").strip().lower()!='n'
        shift = float(prompt("Shift (cm⁻¹) [default=0]: ").strip() or "0")
        ov    = broad is not None and prompt("Overlay sticks? (y/n) [default=y]: ").strip().lower()!='n'
        csv_o = prompt("Save CSV? (y/n) [default=y]: ").strip().lower()!='n'
        png_o = prompt("Save PNG? (y/n) [default=y]: ").strip().lower()!='n'
        out   = "log_spectrum.png" if png_o else None
        ans       = prompt("Auto-trim x-axis? (y/n) [default=y]: ").strip().lower() or "y"
        auto_xlim = ans.startswith('y')
        xlim      = None
        if not auto_xlim:
            xr = prompt("Enter x-limits min,max: ").strip()
            try:
                lo,hi = xr.split(",",1); xlim=(float(lo),float(hi))
            except:
                print("⚠️ Invalid limits, ignoring.")
        plot_log_spectra(valid, broad, norm, shift, axis, ov, csv_o, out,
                         auto_xlim=auto_xlim, xlim=xlim)

    elif mode == '2':
        raw = prompt("CSV files (comma-sep): ",
                     completer=PathCompleter(file_filter=lambda f:f.endswith('.csv'))).strip()
        exps = [s.strip() for s in raw.split(',') if s.strip()]
        valid, bad = [], []
        for f in exps:
            if not os.path.exists(f):
                bad.append(f)
            else:
                valid.append(f)
        if bad:
            print(f"⚠️ Skipping missing CSVs: {', '.join(bad)}")
        if not valid:
            print("❌ No CSVs found."); return
        un    = prompt("CSV x-unit: [1] cm⁻¹  [2] nm  [3] eV (default=3): ").strip() or "3"
        unit  = 'cm' if un=='1' else 'nm' if un=='2' else 'ev'
        norm  = prompt("Normalize? (y/n) [default=y]: ").strip().lower()!='n'
        modec = prompt("Columns: [1]2nd [2]3rd [3]avg [4]both (default=1): ").strip() or "1"
        csv_o = prompt("Save CSV? (y/n) [default=y]: ").strip().lower()!='n'
        png_o = prompt("Save PNG? (y/n) [default=y]: ").strip().lower()!='n'
        out   = "exp_spectrum.png" if png_o else None
        ans       = prompt("Auto-trim x-axis? (y/n) [default=y]: ").strip().lower() or "y"
        auto_xlim = ans.startswith('y')
        xlim      = None
        if not auto_xlim:
            xr = prompt("Enter x-limits min,max: ").strip()
            try:
                lo,hi = xr.split(",",1); xlim=(float(lo),float(hi))
            except:
                print("⚠️ Invalid limits, ignoring.")
        plot_exp_spectra(valid, unit, axis, norm, modec, csv_o, out,
                         auto_xlim=auto_xlim, xlim=xlim)

    else:
        raw = prompt("Log files (comma-sep): ",
                     completer=PathCompleter(file_filter=lambda f:f.endswith('.log'))).strip()
        logs = [s.strip() for s in raw.split(',') if s.strip()]
        valid_logs, bad = [], []
        for f in logs:
            if not os.path.exists(f) or "Final Spectrum" not in open(f, errors='ignore').read():
                bad.append(f)
            else:
                valid_logs.append(f)
        if bad:
            print(f"⚠️ Skipping bad logs: {', '.join(bad)}")
        if not valid_logs:
            print("❌ No valid FC logs."); return

        raw = prompt("CSV files (comma-sep): ",
                     completer=PathCompleter(file_filter=lambda f:f.endswith('.csv'))).strip()
        exps = [s.strip() for s in raw.split(',') if s.strip()]
        valid_exps, bad = [], []
        for f in exps:
            if not os.path.exists(f):
                bad.append(f)
            else:
                valid_exps.append(f)
        if bad:
            print(f"⚠️ Skipping missing CSVs: {', '.join(bad)}")
        if not valid_exps:
            print("⚠️ No CSVs found; proceeding with logs only.")

        bf       = prompt("Broadening FWHM (cm⁻¹) [ENTER=stick only]: ").strip()
        broad    = float(bf) if bf else None
        norm_log = prompt("Normalize logs? (y/n) [default=y]: ").strip().lower()!='n'
        shift    = float(prompt("Shift (cm⁻¹) [default=0]: ").strip() or "0")
        ov       = broad is not None and prompt("Overlay sticks? (y/n) [default=y]: ").strip().lower()!='n'

        un       = prompt("CSV x-unit: [1] cm⁻¹  [2] nm  [3] eV (default=3): ").strip() or "3"
        unit     = 'cm' if un=='1' else 'nm' if un=='2' else 'ev'
        norm_exp = prompt("Normalize exp? (y/n) [default=y]: ").strip().lower()!='n'
        modec    = prompt("Columns: [1]2nd [2]3rd [3]avg [4]both (default=1): ").strip() or "1"

        csv_o    = False   # no combined CSV
        png_o    = prompt("Save combined PNG? (y/n) [default=y]: ").strip().lower()!='n'
        out      = "combined_spectrum.png" if png_o else None

        ans       = prompt("Auto-trim x-axis? (y/n) [default=y]: ").strip().lower() or "y"
        auto_xlim = ans.startswith('y')
        xlim      = None
        if not auto_xlim:
            xr = prompt("Enter x-limits min,max: ").strip()
            try:
                lo,hi = xr.split(",",1); xlim=(float(lo),float(hi))
            except:
                print("⚠️ Invalid limits, ignoring.")

        plot_combined(valid_logs, valid_exps, broad, norm_log, shift, axis,
                      ov, norm_exp, modec, csv_o, out,
                      auto_xlim=auto_xlim, xlim=xlim)

if __name__ == "__main__":
    main()

