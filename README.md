# 🧪 GaussKit

**GaussKit** is a general-purpose Python toolkit for building and automating Gaussian quantum chemistry workflows.

It helps you generate `.com` input files, perform orbital permutations for PIMOM excited-state calculations, add stability jobs, generate Franck–Condon spectra inputs, and manipulate Gaussian inputs with ease.

---

## ⚙️ Features

* ✅ CLI input generator for ground, excited, and stability jobs
* ✅ PIMOM orbital swap builder (HOMO–n ↔ LUMO)
* ✅ Optional `Link1` or separate `.com` for stability jobs
* ✅ Franck–Condon input generator with full control over method, functional, temperature
* ✅ Reads `.xyz` files with flexible formats (tab, space, comma, indexed)
* ✅ Smart extraction of functional and basis from route string or `.com` content
* ✅ Functional auto-detection for MAT/SP file generation
* ✅ Interactive route builder and validation
* ✅ Optional custom basis set footer support
* ✅ Auto-permutation of α/β orbital pairs (e.g. HOMO–1 → LUMO)
* ✅ Job scheduler for GS → ES → FC workflows
* ✅ Contamination analyzer with ideal ⟨S²⟩ value
* ✅ Auto-generated filenames from log or .com file context

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
 [1] PIMOM Swap Generator
 [2] Input Generator
 [3] Franck–Condon Input Builder
 [4] Scheduler
 [5] Log Analyzer
```

---

## 📘 Mode 1 – PIMOM Swap Generator

For excited-state continuation after TDDFT:

* Extracts HOMO/LUMO orbital indices from `.log`
* Prompts for α/β swaps (manual or auto)
* Generates `.com` files for each permutation
* Optionally includes method name in filename
* Ensures correct HOMO/LUMO pair formatting (e.g. 55 56)

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
* Supports commands like `--status` and `--stop`

---

## 📘 Mode 5 – Log Analyzer

* Parses `.log` or `.out` files
* Reports:

  * HOMO/LUMO indices
  * Final SCF energy
  * ⟨S²⟩ expectation value
  * Spring contamination with deviation from ideal ⟨S²⟩
* Color-coded warnings for high spin contamination

---

## 📘 MAT File Generator

* Automatically detects functional used in `.com` file
* Creates `-MAT.com` for single point read-from-checkpoint jobs
* Warns if functional is missing or can't be extracted
* Appends `-MAT.chk` checkpoint file

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
Spectrum=(Broadening=Stick,Lower=-10000.0,Upper=40000.0) Temperature=5.0

H2-ES.chk
TimeIndependent
Output=Matrix=JK
```

---

## 👨‍🔬 Author

**Ali Abou Taka**
Also known as: **Qathota** 🧠
📍 Dearborn, Michigan, USA
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
* GaussView-style coordinate visualization
* Automatic ONIOM model builders
* Conversion between XYZ ↔ Gaussian formats

---

