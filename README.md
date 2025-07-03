# 🧪 GaussKit

**GaussKit** is a general-purpose Python toolkit for building and automating Gaussian quantum chemistry workflows.

It helps you generate `.com` input files, perform orbital permutations for PIMOM excited-state calculations, add stability jobs, and manipulate Gaussian inputs with ease.

---

## ⚙️ Features

- ✅ CLI input generator for ground, excited, and stability jobs
- ✅ PIMOM orbital swap builder (HOMO–n ↔ LUMO)
- ✅ Optional `Link1` or separate `.com` for stability jobs
- ✅ Reads `.xyz` files with flexible formats (tab, space, comma, indexed)
- ✅ Smart extraction of functional and basis from route string
- ✅ Easy route line completions and presets
- ✅ Optional custom basis set footer support
- ✅ Interactive prompts with validation

---

## 🔧 Installation

```bash
git clone https://github.com/aaboutaka/gausskit.git
cd gausskit
pip install -e .
````

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

Then choose one of the modes:

```
Choose mode: [1] PIMOM Swap  [2] Input Generator
```

---

## 📘 Mode 1 – PIMOM Swap Generator

For excited-state continuation after TDDFT:

* Extracts HOMO/LUMO orbital indices from `.log`
* Prompts for alpha/beta swaps (manual or auto)
* Generates `.com` files for each permutation
* Supports HOMO–1, HOMO–2, etc.
* Optionally includes method name in filename

Example:

```text
77 78  (alpha swap)
81 82  (beta swap)
```

---

## 📘 Mode 2 – Gaussian Input Generator

For generating ground- or excited-state inputs:

* Prompts for:

  * Output filename
  * Route line (with completion)
  * Title
  * Charge and multiplicity
  * Path to `.xyz`
  * Optional `@basis_footer.gbs`
  * Optional stability job:

    * `none`: no extra job
    * `link1`: append to same `.com`
    * `separate`: write to `filename-stab.com`

---

## 📦 XYZ Format Support

All the following work:

```
O 0.000000 0.000000 0.1173
H 0.000000 0.757160 -0.4692
H 0.000000 -0.757160 -0.4692
```

```
O,0,0.000000,0.000000,0.1173
H,0,0.000000,0.757160,-0.4692
H,0,0.000000,-0.757160,-0.4692
```

```
O	0.000000	0.000000	0.1173
H	0.000000	0.757160	-0.4692
H	0.000000	-0.757160	-0.4692
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

**Stability Job (Separate)**

```text
%oldchk=mycalc.chk
%chk=mycalc-stab.chk
#p b3lyp guess=read stable=opt chkbasis geom=check

H2O Stability Check

0 1
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
Feel free to use, modify, and contribute.

---

## ✨ Citation

If you use this package in your research:

> Ali Abou Taka. *GaussKit: A Python toolkit for Gaussian input generation and orbital manipulation*. GitHub repository: [https://github.com/aaboutaka/gausskit](https://github.com/aaboutaka/gausskit)

---

## 🔮 Planned Features

* PES/IRC pathway builders
* Gaussian output file parsing
* Conformer generation & batch scan
* GaussView-style coordinate visualization
* Automatic ONIOM model builders
* Conversion between XYZ ↔ Gaussian formats
