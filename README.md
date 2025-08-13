# 🧪 GaussKit

**GaussKit** is a general-purpose Python toolkit for building and automating Gaussian quantum chemistry workflows.

It helps you generate `.com` input files, perform orbital permutations for PIMOM excited-state calculations, add stability jobs, generate Franck–Condon spectra inputs, and manipulate Gaussian inputs with ease.

---

## ⚙️ Features

* ✅ **Interactive CLI with Autocompletion**
  Smart prompts with route/basis/filename completion.
  
* ✅ **PIMOM Swap Generator**
  Swap occupied and virtual orbitals (α/β) for excited-state PIMOM jobs.

* ✅ **Input Generator**
  Build Gaussian `.com` files with route line, title, charge, multiplicity, XYZ input, and optional basis footer. Supports stability jobs (`none`, `link1`, `separate`).

* ✅ **Franck–Condon Input Generator**
  Generate FC inputs with method selection (e.g. `VerticalHessian`), custom functional, temperature, `TimeIndependent`, and matrix options.

* ✅ **Job Scheduler**
  Automate GS → ES → FC workflows with SLURM submission, dependency checking, job ID tracking, and emailing options when jobs are completed.

* ✅ **Benchmark Input Generator**
  Create multiple Gaussian inputs from combinations of functional and basis sets using `.xyz` geometry.

* ✅ **Log Analyzer**
  Extract and report SCF energy, HOMO/LUMO indices, ⟨S²⟩ value, and more.

* ✅ **Vibronic Summary Tool**
  Parse Franck–Condon outputs and generate stick/blurred spectra with optional experimental overlay.

* ✅ **Custom Basis Set Footer Support**
  Include external basis definitions with `@file.gbs`.

* ✅ **Flexible XYZ Parser**
  Accepts tab/space/comma-separated formats.

* ✅ **Auto-generated Filenames**
  File names and checkpoints inferred from context to avoid overwrites and confusion.

* ✅ **Extract XYZ From Log files**
  Pull coordinates from *Standard* or *Input* orientation, optionally writing atom count + comment headers. Skips logs without “Normal termination.”

* ✅ **Energy Comparison for Benchmark Logs**
  Aggregate and compare energies (SCF/ZPE/MP2/PM2/PMP2/TD) by functional+basis or by molecule. Exports CSV/XLSX (if available) and bar-plot PNGs.

* ✅ **Gaussian Error Handler (auto-fix & resubmit)**
  Scans `.log` files for known Gaussian errors (via a YAML database), applies structured route-line fixes (add/remove keywords), writes `.bak`, and can resubmit.

* ✅ **(Optional) Rename Utility**
  Batch-rename Gaussian outputs to a consistent `Molecule_Functional_Basis.ext` convention (and keep `.chk`/batch files in sync).

* ✅ **Z-Matrix Scan Generator**
  Build scan inputs with two modes: **Grid** (all combinations) and **One-at-a-time** (vary one variable holding others fixed).

* ✅ **Scan Results Analyzer/Plotter**
  Parse scan folders, tabulate energies/ΔE and ⟨S²⟩, and emit CSV/Excel/plots for fast comparisons.

* ✅ **Default FC Input from GS/ES Pair**
  Auto-construct a Franck–Condon `.com` from your selected GS/ES `.com` files in the scheduler flow.

---


## 🔧 Installation

```bash
git clone https://github.com/aaboutaka/gausskit.git
cd gausskit
pip install -e .
```

This installs the command:

```bash
gausskit
```

---

## 🧭 Usage

Launch the tool with:

```bash
gausskit
```

Then choose a mode:

```
Choose mode:

[0] Exit                                     [7] Vibronic Summary Tool
[1] PIMOM Swap                               [8] Extract XYZ From Log files
[2] Input Generator                          [9] Energy Comparison for Benchmark Logs
[3] Franck–Condon Input Generator            [10] Error Handler
[4] Job Scheduler                            [11] Rename log files
[5] Benchmark Input Generator                [12] Scan Generator (Z-Matrix)
[6] Log Analyzer CLI                         [13] Analyze and plot Scan outputs
```

---

##  Direct Subcommands

In addition to using the interactive menu, you can launch any mode directly from the command line.
Each subcommand has aliases — you can use the short name, the descriptive name, or the numeric menu option.

```text
gausskit pimom|swap|1         # Mode 1: PIMOM Swap
gausskit input|generate|2     # Mode 2: Input Generator
gausskit fc|franck|3          # Mode 3: Franck–Condon Input Generator
gausskit schedule|scheduler|4 # Mode 4: Job Scheduler
gausskit benchmark|5          # Mode 5: Benchmark Input Generator
gausskit analyze|6 [file|all] # Mode 6: Log Analyzer CLI
gausskit vibronic|7           # Mode 7: Vibronic Summary Tool
gausskit extract|8            # Mode 8: Extract XYZ From Log files
gausskit compare|9            # Mode 9: Energy Comparison for Benchmark Logs
gausskit handle|10            # Mode 10: Error Handler
gausskit rename|11            # Mode 11: Rename log files
gausskit scan|12              # Mode 12: Scan Generator (Z-Matrix)
gausskit plotscan|13          # Mode 13: Analyze and plot Scan outputs
```

**Examples:**

```bash
# Run Mode 5 directly
gausskit benchmark

# Equivalent numeric shortcut
gausskit 5

# Analyze a specific log file
gausskit analyze mycalc.log

# Compare energies for all logs in the current directory
gausskit compare
```

---


## 📘 Mode 1 – PIMOM Swap Generator

For excited-state calculations:

* Extracts HOMO/LUMO orbital indices from `.log`
* Prompts for α/β swaps (manual or auto)
* Generates `.com` files for each permutation
* Optionally includes method name in filename
* Ensures correct HOMO/LUMO pair formatting

---

## 📘 Mode 2 – Gaussian Input Generator

For ground/excited jobs:

* Prompts for:

  * Output filename
  * Route line (with completion)
  * Charge and multiplicity
  * Title
  * `.xyz` coordinates
  * Optional basis footer
* Optionally chains a stability job (`none`, `link1`, `separate`)
* Supports follow-up calculation using previous `.chk` file

---

## 📘 Mode 3 – Franck–Condon Input Generator

For spectrum simulations:

* Asks for:

  * Initial and final `.chk` files
  * Functional
  * Method (e.g. `VerticalHessian`, `AdiabaticHessian`, `AdiabaticShift`, `VerticalGradient`)
  * Temperature
  * Title, charge, multiplicity
* Options:

  * Include `TimeIndependent`
  * Include `Output=Matrix=JK`
* Produces well-formatted FC `.com` input

---

## 📘 Mode 4 – GS/ES/FC Job Scheduler

* Automatically submits:

  * Ground-state job
  * Excited-state (PIMOM) job
  * Franck–Condon job (after GS & ES complete)
* Checks for normal termination
* Tracks SLURM job IDs
* Runs in background
* optional emailing when completed
* 
---

## 📘 Mode 5 – Benchmark Input Generator

Generate a *matrix* of Gaussian inputs by combining one/many functionals with one/many basis sets for each `.xyz` in the current directory.

**What it does**

* Scans the folder for all `*.xyz`.
* Prompts for **functionals** (comma-separated; tab-complete).
* Prompts for **basis sets** (comma-separated; understands parentheses like `6-31+G(d,p)` via smart splitting).
* Prompts for **charge**, **multiplicity**, and **route keywords** (default: `Opt Freq SCF=(fermi, novaracc) int=superfinegrid`).
* If any basis is `gen`/`genecp`, prompts for a **footer** and injects `@file.gbs`.
* Writes a **three-step workflow** per system:

  1. Initial **Stable=Opt** (Guess=Mix) on raw coords
  2. **Optimization + Frequency** with `Geom=AllCheck Guess=Read`
  3. Final **Stable=Opt** on the optimized wavefunction
* Produces clean filenames like:
  `Molecule_Functional_Basis.com` (and corresponding `.chk` / `-stab.chk`).

**How to run**

```bash
gausskit benchmark
# Follow prompts for functionals, basis, charge, multiplicity, keywords
```

**Notes**

* XYZs can be tab/space/comma-delimited; lines like `Atom [idx] x y z` are accepted.
* Functional/basis autocompletion is available.
* Custom basis footers are referenced with `@…` at the correct step(s).

---

## 📘 Mode 6 – Log Analyzer CLI

Parse Gaussian `.log` files and emit a compact report, with optional CSV export (one file per log or combined).

**What it reports**

* Route: **functional/basis**, job types (Opt/Freq/TDDFT/PIMOM/Stable/SP)
* **Charge** / **Multiplicity**
* **SCF energy** (final)
* **α/β HOMO–LUMO** levels and gaps (au → eV conversion when sensible)
* **ZPE** and **thermal enthalpy** corrections (if present)
* **Frequencies** (count + list) and number of **imaginary** modes
* **TDDFT** states (energy and oscillator strength)
* **Dipole** components and total
* **Forces** (Max/RMS)
* **Spin contamination** ⟨S²⟩ with deviation from the ideal value
  → flagged 🟩/🟨/🟥 depending on Δ⟨S²⟩

**How to run**

```bash
# analyze one file, then optionally save CSV
gausskit analyze path/to/file.log

# analyze all logs in the current directory
gausskit analyze all
```

**Exports**

* Per-log: `<file.log>.summary.csv`
* Combined (if chosen): `all_logs_summary.csv`

**Tips**

* If a log did not terminate normally, it’s skipped (or you’ll be prompted, depending on flow).
* Install `pandas` + `XlsxWriter` if you want spreadsheet workflows elsewhere in the toolkit; CSV here works without them.

---

## 📘 Mode 7 – Vibronic Summary Tool

Plot vibronic spectra from **Franck–Condon** Gaussian logs and optionally overlay **experimental** CSVs.

**Modes**

1. **Log-only**: parse “Final Spectrum” sticks from `.log`
2. **Exp-only**: load CSV(s)
3. **Combined**: overlay logs + experimental

**Key options**

* **X-axis units**: `cm⁻¹`, `nm`, or `eV` (auto-convert)
* **Broadening** (FWHM in `cm⁻¹`) to make continuous spectra; optional **overlay sticks**
* **Normalize** (on/off) and **energy shift** (cm⁻¹) for logs
* **Experimental CSV input unit**: `cm⁻¹`, `nm`, or `eV`
* **CSV column mode**: use 2nd, 3rd, average (2nd+3rd)/2, or both
* **Auto-trim x-axis** around non-negligible intensity (or set manual limits)
* **Save outputs**: per-trace CSVs of spectra and `.png` plots

**How to run**

```bash
gausskit vibronic
# Choose 1/2/3; then follow prompts (files, units, broadening, normalize, shift, save)
```

**Outputs**

* Log-only CSV per file: `<base>_spectrum.csv` (cm⁻¹, Intensity)
* Exp-only CSV per file: `<base>_exp_<axis>.csv`
* Plots:

  * Single log → `<base>.png`
  * Single log + exp → `<base>_Exp.png`
  * Multiple logs → `Combined_Logs.png`
  * Multiple logs + exp → `Combined_Logs_Exp.png`
  * Exp-only → `exp_spectrum.png`

**Notes**

* Experimental CSVs should be two or three columns: `x, I1[, I2]`. Negative `x` are skipped before unit conversion.
* When broadening is used, auto-trim ignores very small intensities to focus the view.
---

## 📘 Mode 8 – Extract XYZ From Log files

**What it does:**

* Choose **all** `.log` files or a specific one.
* Extract from **Standard** or **Input** orientation.
* Output either raw XYZ lines or **atom count + comment + XYZ**.

**How to run (direct):**

```bash
gausskit extract
# Follow prompts (orientation, output format)
```

**Notes to add:**

* Skips logs without “Normal termination of Gaussian”.
* Writes `<base>.xyz`.
* Comment line records source log + orientation.

---

## 📘 Mode 9 – Energy Comparison for Benchmark Logs

**What it does:**

* Methods: `scf`, `zpe`, `mp2`, `pm2`, `pmp2`, `td`
* Filter files by molecule prefix and/or an exclusion substring.
* **Grouping modes:** same method (functional+basis), same geometry (molecule), or both.
* Saves **bar plots** `deltaE_<group>.png`.
* Optional **CSV/XLSX** (needs `pandas` + `XlsxWriter`).

**How to run (direct):**

```bash
gausskit compare
# Choose method, filters, and whether to save CSV/XLSX
```

**Outputs:**

* `benchmark_energy_<method>.xlsx` (multiple sheets by group or molecule)
* `benchmark_energy_<method>.csv`
* `skipped_logs_summary.txt` (files that failed checks)

---

## 📘 Mode 10 – Error Handler

**What it does:**

* Processes **all** logs or a comma-list you provide.
* Detects known issues using a **YAML error DB**.
* Applies **structured fixes** to the route line (remove/add keywords).
* Saves a `.bak` of the original input, updates the `.com`, and can **resubmit**.

**How to run (direct):**

```bash
gausskit handle
# Choose logs, choose whether to auto-resubmit
```

**Notes to add:**

* The YAML database is designed to be extensible (per-error patterns + fix blocks).
* Shows which errors were matched and the exact changes applied.

---

## 📘 Mode 11 – Rename log files

> **Add this section to document your conventions.**
> Include:

* **Accepted current patterns** (e.g., `foo-bar.com`, `foo.com`, etc.)
* **Target format:** `Molecule_Functional_Basis.ext`
* Whether the tool simultaneously renames `.chk` and any `.sbatch/.qlog` file.
* **Dry-run** option (if implemented) and collision handling (overwrite? append counter?).

**How to run (direct):**

```bash
gausskit rename
# or the subcommand you wired up; list options here
```

---

## 📘 Mode 12 – Scan Generator (Z-Matrix)

> **Add this section with your exact prompts/options.**
> Document:

* **Inputs:** Z-matrix template, variables to scan, step counts/ranges.
* **Modes:**

  * **Grid** → all combinations across variables.
  * **One-at-a-time** → vary one variable per run, keep others fixed.
* **Output naming** convention per variable/value.
* Optional keywords you inject (e.g., `Opt Freq`, `Stable=Opt`, `int=superfinegrid`, etc.).
* How custom basis/footer and memory/cores are handled (if applicable).

**How to run (direct):**

```bash
gausskit scan
# (or your actual subcommand); describe prompts briefly
```

---

## 📘 Mode 13 – Analyze and plot Scan outputs

> **Add this section to explain outputs.**
> Document:

* **What’s parsed:** energies, ΔE vs. reference (min), ⟨S²⟩, imag. frequencies if present.
* **Exports:** CSV, Excel, and **plots** (line or bar)—file naming and axes.
* **Filtering/grouping:** by variable, by geometry, etc.
* Any **warnings** (non-terminated jobs, missing data) and where they’re logged.

**How to run (direct):**

```bash
gausskit scan-analyze
# (or your actual subcommand); outline prompts
```

---

## 📦 XYZ Format Support

Supports tab, space, or comma-separated formats, with or without atomic numbers:

```xyz
O 0.000000 0.000000 0.1173
H 0.000000 0.757160 -0.4692
H 0.000000 -0.757160 -0.4692
```

---

## 📄 Example Output

**Standard .com**

```text
%chk=mycalc.chk
#p b3lyp/6-31g(d) opt freq scf=(fermi,novaracc)

H2O Optimization

0 1
O 0.000000 0.000000 0.1173
H 0.000000 0.757160 -0.4692
H 0.000000 -0.757160 -0.4692
```

**Stability Job (Link1)**

```text
--Link1--
%chk=mycalc.chk
#p b3lyp guess=read stable=opt chkbasis geom=check

H2O Stability Check

0 1
```

**Franck–Condon**

```text
%oldchk=H2-GS.chk
%chk=H2-ES_fc.chk
#p wb97xd ChkBasis Freq=(ReadFC,FC,ReadFCHT) geom=check guess=read

Franck–Condon spectrum

0 1
Method=VerticalHessian Spectrum=(Broadening=Stick,Lower=-10000.0,Upper=40000.0) Temperature=5.0

H2-ES.chk
TimeIndependent
Output=Matrix=JK
```

---

## 👨‍🔬 Author

**Ali Abou Taka**
📧 [abotaka.ali@gmail.com](mailto:abotaka.ali@gmail.com)
🐙 GitHub: [@aaboutaka](https://github.com/aaboutaka)

---

## 🪪 License

MIT License.
Use, modify, and contribute freely.

---

## ✨ Citation

> Ali Abou Taka. *GaussKit: A Python toolkit for Gaussian input generation and orbital manipulation*. GitHub repository: [https://github.com/aaboutaka/gausskit](https://github.com/aaboutaka/gausskit)

---

## 🔮 Planned Features

* PES/IRC pathway builders
* Gaussian output file parsing
* Conformer generation & batch scan
* Conversion between XYZ ↔ Gaussian formats

---

