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
[0] Exit
[1] PIMOM Swap
[2] Input Generator
[3] Franck–Condon Input Generator
[4] Job Scheduler
[5] Benchmark Input Generator
[6] Log Analyzer CLI
[7] Vibronic Summary Tool
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
---

## 📘 Mode 5 – Log Analyzer

* Parses `.log` files
* Reports:

  * HOMO/LUMO indices and energy gaps
  * Final SCF energy
  * ⟨S²⟩ expectation value
  * Type of calculations
  * print out frequencies and check if there is any imaginary frequency
  * Spring contamination with deviation from ideal ⟨S²⟩
* Color-coded warnings for high spin contamination

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

