import os
import re
import shutil
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter, PathCompleter
from gausskit.completions import tab_autocomplete_prompt, HybridCompleter
from gausskit.utils import safe_float_input, add_modredundant_to_opt
from gausskit.utils import parse_int_csv, clean_token, MultiPathCompleter
import itertools

def read_xyz_file(xyz_path):
    """Read an XYZ file, handling both standard (N+comment) and headerless formats.
    Returns: list of lines like 'C  0.00000000  0.00000000  0.00000000'
    """
    try:
        with open(xyz_path, 'r') as f:
            raw = [ln.strip() for ln in f if ln.strip()]

        if not raw:
            return []

        coords = []
        # Case 1: Standard XYZ with atom count on first line
        try:
            n_atoms = int(raw[0])
            records = raw[2:2+n_atoms]   # skip atom count + comment
        except ValueError:
            # Case 2: Headerless: take all lines
            records = raw

        for line in records:
            parts = re.split(r'[,\s]+', line.strip())
            if len(parts) < 4:
                continue
            atom = parts[0]
            try:
                x, y, z = map(float, parts[-3:])
            except ValueError:
                continue
            coords.append(f"{atom:2s} {x: .8f} {y: .8f} {z: .8f}")

        return coords

    except Exception as e:
        print(f"❌ Failed to read XYZ file {xyz_path}: {e}")
        return []


def create_gaussian_input():
    import os, re
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter, PathCompleter

    print("=" * 75)
    print("📄 Gaussian Input File Generator")
    print("    - Generates .com with 3 stages: Stability → Main Job → Stability")
    print("    - Supports %OldChk at the very top, and gen/genecp basis handling.")
    print("=" * 75)

    filename = prompt("Enter name for output .com file (without extension): ").strip()
    if not filename:
        print("❌ No filename provided.")
        return

    # ---- Route presets + entry ----
    routes = [
        "b3lyp/6-31g(d) opt freq int=superfinegrid scf=(fermi,novaracc)",
        "cam-b3lyp/def2tzvp td(nstates=10) int=superfinegrid scf=(fermi,novaracc)",
        "wb97xd/6-311++g(d,p) opt=tight freq int=superfinegrid scf=(fermi,novaracc)",
        "hf/6-31g sp int=superfinegrid scf=(fermi,novaracc)",
        "m06-2x/cc-pvtz opt freq int=superfinegrid scf=(fermi,novaracc)",
        "pbe0/def2svp opt freq int=superfinegrid scf=(fermi,novaracc)",
        "m062x/def2tzvp ts freq int=superfinegrid scf=(fermi,novaracc)",
        "wb97mv/def2tzvppd sp int=superfinegrid scf=(fermi,novaracc)",
        "b3lyp/def2svp opt freq=noraman int=superfinegrid scf=(fermi,novaracc)",
        "tpssh/cc-pvtz opt=modredundant freq int=superfinegrid scf=(fermi,novaracc)"
    ]
    route_completer = WordCompleter(routes, ignore_case=True)
    route_raw = prompt("Enter Gaussian route line (TAB for presets): ", completer=route_completer).strip()

    # ---- Helpers -------------------------------------------------------------
    def normalize_route(r: str) -> str:
        """Add '#p'; fold standalone 'gen/genecp' tokens into METHOD/GEN; strip extra leading #."""
        r = (r or "").strip()
        if not r:
            return "#p"
        if r.startswith("#"):
            r = r.lstrip("#").lstrip("pP").lstrip()
        toks = r.split()
        if not toks:
            return "#p"
        first = toks[0]
        tl = [t.lower() for t in toks]
        if "/" not in first:
            if "genecp" in tl:
                toks = [first + "/genecp"] + [t for t in toks[1:] if t.lower() != "genecp"]
            elif "gen" in tl:
                toks = [first + "/gen"] + [t for t in toks[1:] if t.lower() != "gen"]
        return "#p " + " ".join(toks)

    def _method_basis(route_norm: str):
        """Return (method, basis) from normalized route '#p method/basis ...'."""
        toks = (route_norm or "").split()
        if len(toks) >= 2:
            mb = toks[1]
            if "/" in mb:
                method, basis = mb.split("/", 1)
            else:
                method, basis = mb, ""
            return method, basis
        return "", ""

    def _route_uses_gen(route_raw_in: str, route_norm_in: str) -> bool:
        """Detect 'gen' or 'genecp' anywhere (raw or normalized)."""
        toks_raw = route_raw_in.replace("#", " ").replace("/", " ").split()
        if any(t.lower() in ("gen", "genecp") for t in toks_raw):
            return True
        toks_norm = route_norm_in.split()
        if len(toks_norm) >= 2:
            mb = toks_norm[1].lower()
            if "/gen" in mb or "/genecp" in mb:
                return True
        s = f" {route_norm_in.lower()} "
        return " gen " in s or " genecp " in s

    def _ensure_token(s: str, token: str) -> str:
        return s if token.lower() in s.lower() else (s + " " + token)

    def _remove_token(s: str, token: str) -> str:
        return re.sub(rf"(?i)\b{re.escape(token)}\b", "", s).replace("  ", " ").strip()

    # ---- Normalize + extract method/basis -----------------------------------
    route = normalize_route(route_raw)
    method_token, basis_token_norm = _method_basis(route)

    # Also capture user's extra flags (after first token) to carry into stage-2
    toks = route.split()
    rest_flags = " ".join(toks[2:]) if len(toks) > 2 else ""

    # ---- Optional %OldChk at the very top -----------------------------------
    add_old = (prompt("Add %OldChk at the top? [y/N]: ").strip().lower() or "n").startswith("y")
    oldchk = ""
    if add_old:
        oldchk = prompt("Select %OldChk file (TAB to browse): ",
                        completer=MultiFilePathCompleter()).strip()
        if not oldchk or not os.path.exists(oldchk):
            print(f"❌ OldChk file '{oldchk}' not found.")
            cont = (prompt("Continue without %OldChk? [Y/n]: ").strip().lower() or "y").startswith("y")
            if cont:
                add_old = False
                oldchk = ""
            else:
                oldchk = prompt("Select %OldChk file (TAB to browse): ",
                                completer=MultiFilePathCompleter()).strip()
                if not oldchk or not os.path.exists(oldchk):
                    print(f"❌ OldChk file '{oldchk}' not found. Aborting.")
                    return

    # If reading from %OldChk, ask whether to reuse basis from the checkpoint
    use_chkbasis = False
    if add_old:
        use_chkbasis = (prompt("When using %OldChk, reuse basis from checkpoint (ChkBasis)? [Y/n]: ")
                        .strip().lower() or "y").startswith("y")

    # Build the "method[/basis]" part respecting ChkBasis rule:
    #   - If ChkBasis is used, DO NOT attach '/basis' (Gaussian would error).
    base_mb = method_token if use_chkbasis else (
        f"{method_token}/{basis_token_norm}" if basis_token_norm else method_token
    )

    # ---- gen/genecp basis footer handling -----------------------------------
    using_gen = _route_uses_gen(route_raw, route)
    need_basis_footer = using_gen and (not add_old or (add_old and not use_chkbasis))

    basis_block = ""   # embedded content
    basis_ref   = ""   # @file reference
    if need_basis_footer:
        basis_path = prompt(
            "GEN/GENECP detected. Enter basis file (e.g., SDD.gbs): ",
            completer=MultiFilePathCompleter()).strip()

        if not basis_path or not os.path.exists(basis_path):
            print(f"❌ Basis set file '{basis_path}' not found.")
            cont = (prompt("Continue without a gen/genecp basis footer? [y/N]: ")
                    .strip().lower() or "n").startswith("y")
            if not cont:
                return
        else:
            embed = (prompt("Embed basis content in stage-1? [y/N]: ")
                     .strip().lower() or "N").startswith("y")
            if embed:
                with open(basis_path, 'r', encoding="utf-8", errors="ignore") as bf:
                    basis_block = "\n" + bf.read().strip() + "\n"
            else:
                basis_ref = f"@{basis_path}\n"

    # ---- Title / charge / mult / geometry -----------------------------------
    title = prompt("Enter title (or press ENTER for default): ").strip() or "Gaussian input file generated by GaussKit"
    charge = prompt("Enter total charge (default 0): ").strip() or "0"
    multiplicity = prompt("Enter multiplicity (default 1): ").strip() or "1"

    coords_str = ""
    if not add_old:
        xyz_completer = WordCompleter([f for f in os.listdir() if f.lower().endswith('.xyz')], ignore_case=True)
        xyz_file = prompt("Enter path to XYZ coordinates file: ", completer=xyz_completer).strip()
        coords = read_xyz_file(xyz_file)
        if not coords:
            print("❌ No valid coordinates found.")
            return
        coords_str = "\n".join(coords)

    # ---- Build 3-stage routes ------------------------------------------------
    # Stage-1: Stability
    if add_old:
        # read geom+guess from chk; add chkbasis ONLY if reusing basis
        route_stab1 = f"#p {base_mb} stable=opt guess=read geom=check"
        if use_chkbasis:
            route_stab1 = _ensure_token(route_stab1, "chkbasis")
    else:
        # no OldChk: provide coords (and possible gen/genecp footer)
        route_stab1 = f"#p {base_mb} stable=opt scf=xqc int=superfinegrid"

    # Stage-2: Main job (rebuild from method[/basis] + user's flags, then ensure continuation tokens)
    route_main = f"#p {method_token} {rest_flags} int=superfinegrid".strip()
    for tok in ("guess=read", "geom=check"):
        route_main = _ensure_token(route_main, tok)

    route_main = _ensure_token(route_main, "chkbasis")
    route_main = route_main.strip()

    # Stage-3: Stability again
    route_stab2 = f"#p {method_token} stable=opt"
    for tok in ("guess=read", "geom=check"):
        route_stab2 = _ensure_token(route_stab2, tok)
    route_stab2 = _ensure_token(route_stab2, "scf=xqc")
    route_stab2 = _ensure_token(route_stab2, "int=superfinegrid")
    route_stab2 = _ensure_token(route_stab2, "chkbasis")
    route_stab2 = route_stab2.strip()

    # ---- Write file (3 links) ------------------------------------------------
    output_path = filename + ".com"
    with open(output_path, "w", encoding="utf-8") as f:
        # ----- Stage 1 -----
        if add_old:
            f.write(f"%OldChk={oldchk}\n")
        f.write(f"%Chk={filename}_stab.chk\n")
        f.write(route_stab1 + "\n\n")
        f.write(f"{title} [1/3: Stability]\n\n")
        f.write(f"{charge} {multiplicity}\n")
        if not add_old:
            # geometry present
            f.write(coords_str.rstrip() + "\n\n")
            if need_basis_footer and (basis_block or basis_ref):
                f.write(basis_block if basis_block else basis_ref)
        else:
            # geom=check: no coordinates
            f.write("\n")
            # If overriding basis (no ChkBasis) and using gen/genecp, supply footer
            if need_basis_footer and not use_chkbasis and (basis_block or basis_ref):
                f.write(basis_block if basis_block else basis_ref)

        # ----- Stage 2 -----
        f.write("--Link1--\n")
        f.write(f"%OldChk={filename}_stab.chk\n")
        f.write(f"%Chk={filename}.chk\n")
        f.write(route_main + "\n\n")
        f.write(f"{title} [2/3: Main Job]\n\n")
        f.write(f"{charge} {multiplicity}\n\n")  # geom=check: no coords
        if need_basis_footer and not use_chkbasis and (basis_block or basis_ref):
            f.write(basis_block if basis_block else basis_ref)

        # ----- Stage 3 -----
        f.write("--Link1--\n")
        f.write(f"%OldChk={filename}.chk\n")
        f.write(f"%Chk={filename}_stab.chk\n")
        f.write(route_stab2 + "\n\n")
        f.write(f"{title} [3/3: Stability]\n\n")
        f.write(f"{charge} {multiplicity}\n\n")  # geom=check: no coords
        if need_basis_footer and not use_chkbasis and (basis_block or basis_ref):
            f.write(basis_block if basis_block else basis_ref)

    print(f"\n✅ 3-stage input file created: {output_path}")


def smart_split_basis_sets(basis_input):
    tokens = []
    current = ''
    depth = 0
    for char in basis_input:
        if char == ',' and depth == 0:
            if current.strip():
                tokens.append(current.strip())
                current = ''
        else:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            current += char
    if current.strip():
        tokens.append(current.strip())
    return tokens


def clean_label(s):
    # Replace '+' with 'p', remove '-', '(', ')', ',' and all whitespace
    return re.sub(r'[,\s\-\(\)]', '', s.replace('+', 'p'))


def create_benchmark_inputs():
    print("=" * 60)
    print("Benchmark Input Generator: XYZ → .com for each functional/basis set")
    print("=" * 60)

    # Discover available XYZs in cwd
    xyz_files = [f for f in os.listdir() if f.lower().endswith(".xyz")]
    if not xyz_files:
        print("⚠️  No .xyz files found in the current directory.")
    else:
        print(f"Found {len(xyz_files)} .xyz file(s).")

    # --- Preset lists ---------------------------------------------------------
    DFT_FUNCTIONALS = [
        # General Hybrid and GGA
        'HF', 'BLYP', 'PBE', 'PBE0', 'TPSSh',
        'B3LYP', 'B3P86', 'B3PW91', 'O3LYP',
        # Dispersion-Corrected
        'APFD', 'APF', 'wB97XD',
        # Long-Range-Corrected
        'LC-wHPBE', 'LC-wPBE', 'CAM-B3LYP', 'wB97X', 'wB97',
        # Truhlar Group
        'MN15', 'M11', 'SOGGA11X', 'N12SX', 'MN12SX',
        'PW6B95', 'PW6B95D3', 'M08HX',
        'M06', 'M06HF', 'M062X', 'M05', 'M052X',
        # PBE Correlation-Based Hybrids
        'PBE1PBE', 'HSEH1PBE', 'OHSE2PBE', 'OHSE1PBE', 'PBEh1PBE',
        # One-Parameter Hybrids
        'B1B95', 'B1LYP', 'mPW1PW91', 'mPW1LYP', 'mPW1PBE', 'mPW3PBE',
        # B97 Revisions
        'B98', 'B971', 'B972',
        # τ-dependent hybrids
        'tHCTHhyb', 'BMK',
        # Older/Legacy Hybrids
        'X3LYP', 'HISSbPBE',
        # Half-and-Half Hybrids
        'BHandH', 'BHandHLYP',
        # Exchange-only Functionals
        'PW91', 'mPW', 'G96', 'O', 'TPSS', 'RevTPSS', 'BRx', 'PKZB', 'wPBEh', 'PBEh',
        # Correlation-only Functionals
        'VWN', 'VWN5', 'LYP', 'PL', 'P86', 'PW91', 'B95',
        'TPSS', 'RevTPSS', 'KCIS', 'BRC', 'PKZB',
        # Combined correlation variations
        'VP86', 'V5LYP',
        # Standalone Pure Functionals
        'VSXC', 'HCTH', 'HCTH93', 'HCTH147', 'HCTH407', 'tHCTH',
        'B97D', 'B97D3',
        'M06L', 'SOGGA11', 'M11L', 'MN12L', 'N12', 'MN15L'
    ]

    BASIS_SETS = [
        # Minimal and Split-Valence
        'STO-3G', '3-21G', '6-21G', '4-31G',
        '6-31G', '6-31G(d)', '6-31+G(d,p)', "6-31G(d')", "6-31G(d',p')",
        '6-311G', '6-311+G(d)', '6-311+G(d,p)', '6-311++G(d,p)',
        # Dunning correlation-consistent
        'cc-pVDZ', 'cc-pVTZ', 'cc-pVQZ', 'cc-pV5Z', 'cc-pV6Z',
        'aug-cc-pVDZ', 'aug-cc-pVTZ', 'aug-cc-pVQZ', 'aug-cc-pV5Z', 'aug-cc-pV6Z',
        'daug-cc-pVDZ', 'daug-cc-pVTZ', 'spaug-cc-pVDZ', 'jul-cc-pVDZ',
        'Jun-cc-pVDZ', 'May-cc-pVDZ', 'Apr-cc-pVDZ',
        # Ahlrichs/Weigend def2 sets
        'def2-SVP', 'def2-SVPP', 'def2-TZVP', 'def2-TZVPP',
        'def2-QZVP', 'def2-QZVPP',
        # ECP & pseudopotentials
        'LanL2MB', 'LanL2DZ', 'SDD', 'SDDAll',
        'CEP-4G', 'CEP-31G', 'CEP-121G',
        'SHC', 'SEC',
        # D95 and variations
        'D95', 'D95V',
        # Other built-ins and specialty
        'SV', 'SVP', 'TZV', 'TZVP', 'QZVP',
        'MidiX', 'MTSmall', 'CBSB7',
        'EPR-II', 'EPR-III',
        'DGDZVP', 'DGDZVP2', 'DGTZVP',
        'UGBS', 'UGBS1P', 'UGBS2P', 'UGBS3P',
        'UGBS1V', 'UGBS2V', 'UGBS3V',
        'UGBS1O', 'UGBS2O', 'UGBS3O',
        # Generic/genecp
        'gen', 'genecp'
    ]

    functional_completer = WordCompleter(DFT_FUNCTIONALS, ignore_case=True)
    basis_completer      = WordCompleter(BASIS_SETS,      ignore_case=True)

    # --- Inputs ---------------------------------------------------------------
    raw_funcs = prompt("Enter functional(s) (comma-separated): ",
                       completer=functional_completer).strip()
    functionals = [f.strip() for f in raw_funcs.split(",") if f.strip()]

    raw_basis_input = prompt(
        "Enter basis set(s) (e.g. 6-31G, 6-31+G(d,p), def2-TZVP): ",
        completer=basis_completer
    ).strip()
    basis_sets = smart_split_basis_sets(raw_basis_input)
    basis_sets = [b.strip() for b in basis_sets if b.strip()]

    # --- Charge/Multiplicity modes -------------------------------------------
    pairs = []
    mode = prompt(
        "Charge/Multiplicity mode:\n"
        "  [1] Single charge + single multiplicity\n"
        "  [2] Multiple charges (same or different multiplicities)\n"
        "  [3] Explicit pairs (e.g., 0/1, -1/2, 1/2)\n"
        "  [4] Single charge + multiple multiplicities\n"
        "[default: 1]: "
    ).strip() or "1"

    if mode == "3":
        raw = prompt("Enter charge/multiplicity pairs (e.g., 0/1, -1/2, 1/2): ").strip()
        for tok in raw.split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                q_s, m_s = tok.split("/", 1)
                q = int(q_s.strip()); m = int(m_s.strip())
                pairs.append((q, m))
            except Exception:
                print(f"[warn] Skipping invalid pair: {tok!r}")
        if not pairs:
            print("[warn] No valid pairs entered; defaulting to 0/1.")
            pairs = [(0, 1)]

    elif mode == "2":
        charges = parse_int_csv(prompt("Enter charges (comma-separated, e.g., 0, -1, 1): ").strip())
        if not charges:
            print("[warn] No charges entered; defaulting to 0.")
            charges = [0]
        same_mult = (prompt("Same multiplicity for all charges? [Y/n]: ").strip().lower() or "y").startswith("y")
        if same_mult:
            m = int(prompt("Multiplicity [default=1]: ").strip() or "1")
            pairs = [(q, m) for q in charges]
        else:
            mults = parse_int_csv(prompt(
                "Enter multiplicities (comma-separated; same length as charges), "
                "or press ENTER to set per charge: "
            ).strip())
            if mults and len(mults) == len(charges):
                pairs = list(zip(charges, mults))
            else:
                for q in charges:
                    m = int(prompt(f"Multiplicity for charge {q} [default=1]: ").strip() or "1")
                    pairs.append((q, m))

    elif mode == "4":
        # NEW: Single charge + multiple multiplicities
        q = int(prompt("Charge [default=0]: ").strip() or "0")
        mults = parse_int_csv(prompt("Enter multiplicities (comma-separated, e.g., 1, 3, 5): ").strip())
        if not mults:
            print("[warn] No multiplicities entered; defaulting to 1.")
            mults = [1]
        pairs = [(q, m) for m in mults]
        # Optional: filename style for this mode
        fname_style = (prompt(
            "Filename style for single charge + multiple multiplicities?\n"
            "  [1] Standard: <mol>_<func>_<basis>_q<q>_m<m>.com  (default)\n"
            "  [2] Condensed: <mol>_<m>_<func>_<basis>.com  (omit charge)\n"
            "[default: 1]: "
        ).strip() or "1")
    else:
        q = int(prompt("Charge [default=0]: ").strip() or "0")
        m = int(prompt("Multiplicity [default=1]: ").strip() or "1")
        pairs = [(q, m)]


    # --- Keywords -------------------------------------------------------------
    keywords = prompt("Enter route keywords (default: Opt Freq SCF=(fermi, novaracc) int=superfinegrid): ").strip()
    if not keywords:
        keywords = "Opt Freq SCF=(fermi, novaracc) int=superfinegrid"

    # --- Custom basis footer (for gen/genecp) --------------------------------
    needs_custom_basis = any(b.lower() in ("gen", "genecp") for b in basis_sets)
    custom_basis_map = {}
    
    if needs_custom_basis:
        expanded_basis_sets = []
        for basis in basis_sets:
            bl = basis.lower()
            if bl not in ("gen", "genecp"):
                expanded_basis_sets.append(basis)
                continue
    
            msg = f"Enter basis set file(s) for '{basis}' (comma-separated if multiple): "
            raw_files = prompt(msg, completer=PathCompleter()).strip()
            files = [f.strip() for f in raw_files.split(",") if f.strip()]
            if not files:
                print(f"[warn] No files given for {basis}, skipping.")
                continue
    
            for i, file in enumerate(files, 1):
                tag = f"{basis}{i}"  # e.g. gen1, gen2, genecp1, genecp2
                expanded_basis_sets.append(tag)
                if os.path.exists(file):
                    custom_basis_map[tag.lower()] = f"@{file}\n"
                else:
                    print(f"⚠️ File {file} not found. Referencing as @{file}. You must supply it later.")
                    custom_basis_map[tag.lower()] = f"@{file}\n"
    
        basis_sets = expanded_basis_sets


    # --- Generate for every XYZ in cwd ---------------------------------------
    for xyz in xyz_files:
        coords = read_xyz_file(xyz)  # Expect list like ["C 0.0 0.0 0.0", ...]
        # print(coords)
        # Reformat to fixed-point to avoid scientific notation
        fixed_lines = []
        for ln in coords:
            parts = ln.split()
            if len(parts) >= 4:
                el = parts[0]
                try:
                    x = float(parts[1]); y = float(parts[2]); z = float(parts[3])
                    fixed_lines.append(f"{el:2s} {x: .8f} {y: .8f} {z: .8f}")
                except Exception:
                    # Fallback: keep original if parsing fails
                    fixed_lines.append(ln.strip())
            else:
                fixed_lines.append(ln.strip())
        coords_str = "\n".join(fixed_lines)

        molname = xyz[:-4]

        for func in functionals:
            func_token = func.strip()
            func_core  = func_token.split("/", 1)[0]   # keep method only if user typed "B3LYP/..."
            func_clean = clean_token(func_core)

            for basis in basis_sets:
                basis_token = basis.strip()
                basis_clean = clean_token(basis_token)
            
                # Detect if this is a numbered custom basis (e.g., gen1, genecp2)
                if basis_clean.lower().startswith("genecp"):
                    basis_in_route = "genecp"
                elif basis_clean.lower().startswith("gen"):
                    basis_in_route = "gen"
                else:
                    basis_in_route = basis_token
            
                # Build route line; sanitize keywords to avoid '# #p' duplication
                kw = (keywords or "").strip()
                if kw.startswith("#"):
                    kw = kw.lstrip("#").lstrip("pP").lstrip()
                route_line = f"#p {func_core}/{basis_in_route} {kw}".rstrip()


                # Build route line; sanitize keywords to avoid '# #p' duplication
                kw = (keywords or "").strip()
                if kw.startswith("#"):
                    kw = kw.lstrip("#").lstrip("pP").lstrip()
                route_line = f"#p {func_core}/{basis_in_route} {kw}".rstrip()

                for (q, m) in pairs:
                    base_name = f"{molname}_{func_clean}_{basis_clean}_q{q}_m{m}"
                    out_name  = f"{base_name}.com"
                    chk_name_stab  = f"{base_name}_stab.chk"
                    chk_name  = f"{base_name}.chk"
                    title = f"{molname} — {func_core}/{basis_token}   q={q} m={m}"

                    # Build the 3 route lines
                    route_stab1   = f"#p {func_core}/{basis_in_route} stable=opt scf=novaracc guess=mix int=superfinegrid".rstrip()
                    route_optfreq = f"#p {func_core} guess=read chkbasis geom=allcheck {keywords}".rstrip()
                    route_stab2   = f"#p {func_core} stable=opt guess=read chkbasis geom=allcheck int=superfinegrid".rstrip()
                    
                    with open(out_name, "w", encoding="utf-8") as f:
                        # ----- Stage 1: Stability (with geometry & optional custom basis) -----
                        f.write(f"%chk={chk_name_stab}\n")
                        f.write(route_stab1 + "\n\n")
                        f.write(f"{molname} — {func_core}/{basis_token}   q={q} m={m}   [1/3: Stability]\n\n")
                        f.write(f"{q} {m}\n")
                        f.write(coords_str.rstrip() + "\n\n")
                        if basis_clean.lower() in custom_basis_map:
                            f.write(custom_basis_map[basis_clean.lower()].rstrip() + "\n")
                                            
                        # ----- Stage 2: Opt+Freq (read geom/basis/guess from chk) -----
                        f.write("--Link1--\n")
                        f.write(f"%oldchk={chk_name_stab}\n")
                        f.write(f"%chk={chk_name}\n")

                        f.write(route_optfreq + "\n\n")
                        f.write(f"{molname} — {func_core}/{basis_token}   q={q} m={m}   [2/3: Opt+Freq]\n\n")
                    
                        # ----- Stage 3: Stability again (final check) -----
                        f.write("--Link1--\n")
                        f.write(f"%oldchk={chk_name}\n")
                        f.write(f"%chk={chk_name_stab}\n")
                        f.write(route_stab2 + "\n\n")
                        f.write(f"{molname} — {func_core}/{basis_token}   q={q} m={m}   [3/3: Stability]\n\n")


                    print(f"✔ Wrote {out_name}")


def create_default_fc_input(gs_base: str, es_base: str) -> str:
    """
    Read gs_base.com and es_base.com, extract:
      - oldchk  ← from es_base %chk=
      - route   ← from es_base “#P …”
      - charge, mult ← from es_base first “X Y” line
    and write es_base_fc.com → es_base_fc.chk
    Returns the FC base name (without .com).
    """

    def extract_chk(com_path):
        with open(com_path) as f:
            for L in f:
                L = L.strip()
                if L.lower().startswith('%chk='):
                    return L.split('=',1)[1]
        # fallback
        return os.path.splitext(com_path)[0] + '.chk'

    def extract_route(com_path):
        with open(com_path) as f:
            for L in f:
                if L.lower().startswith('#p'):
                    return L.strip()[2:].strip()
        raise RuntimeError(f"No route line (#P) in {com_path}")

    def extract_charge_mult(com_path):
        with open(com_path) as f:
            lines = [l.rstrip() for l in f]
        # skip headers, find title then next nonblank = charge multiplicity
        seen_title = False
        for L in lines:
            if not L.startswith(('%', '#')) and L.strip():
                if not seen_title:
                    seen_title = True
                else:
                    parts = L.split()
                    if len(parts) >= 2:
                        return parts[0], parts[1]
        return "0", "1"

    gs_com = gs_base + '.com'
    es_com = es_base + '.com'

    oldchk_GS = extract_chk(gs_com)
    oldchk_ES = extract_chk(es_com)
    route = extract_route(es_com)
    charge, mult = extract_charge_mult(es_com)

    fc_base = f"{es_base}_fc"
    fc_com  = fc_base + '.com'
    fc_chk  = fc_base + '.chk'

    with open(fc_com, 'w') as out:
        out.write(f"%oldchk={oldchk_GS}\n")
        out.write(f"%chk={fc_chk}\n")
        out.write(f"#P ChkBasis Freq=(ReadFC,FC,ReadFCHT) Geom=Checkpoint NOSYMM Guess=Read\n\n")
        out.write(f"Franck–Condon Calculation: {es_base}\n\n")
        out.write(f"{charge} {mult}\n\n")
        out.write("Spectrum=(Broadening=Stick,Lower=-10000.0,Upper=40000.0) temperature=298.15\n\n")
        out.write(f"{oldchk_ES}\n")
    print(f"✅ Default FC input generated: {fc_com}")
    return fc_base



#def write_pimom_input(base_log, alpha_swaps, beta_swaps, charge, multiplicity,
#                      method, footer=None, include_func_in_name=True, custom_oldchk=None):
#    base_name = os.path.splitext(base_log)[0]
#    oldchk = custom_oldchk if custom_oldchk else base_name + ".chk"
#
#    suffix = ""
#    if alpha_swaps:
#        suffix += "-a" + "-".join("_".join(pair) for pair in alpha_swaps)
#    if beta_swaps:
#        suffix += "-b" + "-".join("_".join(pair) for pair in beta_swaps)
#    if include_func_in_name:
#        suffix += f"-{method}"
#
#    outchk = base_name + suffix + ".chk"
#    comfile = base_name + suffix + ".com"
#
#    with open(comfile, "w") as f:
#        f.write(f"%oldchk={oldchk}\n")
#        f.write(f"%chk={outchk}\n")
#        f.write(f"#p {method} scf=(pimom,fermi,novaracc) integral=SuperFineGrid guess=(alter,read) geom=check chkbasis int=noxctest\n\n")
#        f.write("Title Card Required\n\n")
#        f.write(f"{charge} {multiplicity}\n\n")
#
#        for pair in alpha_swaps:
#            f.write(" ".join(pair) + " ! alpha swap\n")
#        if alpha_swaps and beta_swaps:
#            f.write("\n")
#        for pair in beta_swaps:
#            f.write(" ".join(pair) + " ! beta swap\n")
#
#        f.write("\n\n")
#        if footer:
#            f.write(f"@{footer}\n")
#
#    print(f"\n✅ Created file: {comfile}")
#    print(f"   → Using %oldchk: {oldchk}")
#    print(f"   → Output %chk  : {outchk}")

periodic_table = [
    "",  # index 0 unused
    "H",  "He", "Li", "Be", "B",  "C",  "N",  "O",  "F",  "Ne",
    "Na", "Mg", "Al", "Si", "P",  "S",  "Cl", "Ar", "K",  "Ca",
    "Sc", "Ti", "V",  "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y",  "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I",  "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W",  "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U",  "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og"
]


def extract_xyz_from_log(logfile_path, orientation="standard"):
    """
    Extract XYZ coordinates from a Gaussian .log file.
    `orientation` = "standard" or "input"
    Returns: list of strings like ["C 0.000 0.000 0.000", ...]
    """
    if not os.path.exists(logfile_path):
        print(f"❌ File not found: {logfile_path}")
        return None

    keyword = "Standard orientation" if orientation == "standard" else "Input orientation"

    with open(logfile_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    block_start = None
    for i, line in enumerate(lines):
        if keyword in line:
            block_start = i
    if block_start is None:
        print(f"❌ Could not find orientation: {keyword}")
        return None

    # Skip 5 header lines
    block = lines[block_start+5:]
    xyz_lines = []
    for line in block:
        if "----" in line or len(line.strip()) == 0:
            break
        tokens = line.split()
        atomic_number = int(tokens[1])
        if 0 < atomic_number < len(periodic_table):
            symbol = periodic_table[atomic_number]
        else:
            symbol = "X"

        x = float(tokens[3]); y = float(tokens[4]); z = float(tokens[5])
        xyz_lines.append(f"{symbol:2s} {x: .8f} {y: .8f} {z: .8f}")

    return xyz_lines


def extract_xyz_cli():
    """
    Interactive CLI for extracting XYZ from log files.
    """
    print("=" * 60)
    print("🧪 Gaussian Log to XYZ Extractor")
    print("    - Extracts coordinates from Input or Standard orientation")
    print("    - Can include atom count and comment line")
    print("=" * 60)

    # Ask: all or one
    all_files = prompt("Extract from ALL .log files in this directory? [y/N]: ").strip().lower().startswith("y")
    if all_files:
        log_files = [f for f in os.listdir() if f.endswith(".log")]
    else:
        log_completer = WordCompleter([f for f in os.listdir() if f.endswith('.log')])
        selected = prompt("Select log file: ", completer=log_completer).strip()
        if not os.path.exists(selected):
            print(f"❌ File does not exist: {selected}")
            return
        log_files = [selected]

    if not log_files:
        print("❌ No .log files found.")
        return

    # Ask: orientation
    orient_choice = prompt("Orientation? [0] Standard  [1] Input (default: 0): ").strip()
    orientation = "input" if orient_choice == "1" else "standard"

    # Ask: format
    fmt_choice = prompt("Output format? [0] Only XYZ lines  [1] Atom count + comment + XYZ (default: 1): ").strip()
    include_count = fmt_choice != "0"

    for log_file in log_files:
        if "Normal termination" not in open(log_file, errors='ignore').read():
            print(f"⚠️ Skipping {log_file}: did not terminate normally.")
            continue

        coords = extract_xyz_from_log(log_file, orientation)
        if not coords:
            print(f"❌ Failed to extract from {log_file}")
            continue

        base = os.path.splitext(log_file)[0]
        outname = base + ".xyz"

        with open(outname, "w") as f:
            if include_count:
                f.write(f"{len(coords)}\n")
                f.write(f"{log_file} — {orientation} orientation\n")
            for line in coords:
                f.write(line + "\n")

        print(f"✅ Extracted XYZ written to: {outname}")

def generate_zmatrix_scan_inputs():
    """
    Generate Gaussian input files by scanning Z-matrix internal coordinates.

    Supported scan modes:
    [1] All variables vary together (synchronized)
    [2] Grid of all combinations
    [3] One-at-a-time (others held fixed at start)

    Input format:
    - Z-matrix using variables like R1, A1, D1
    - Followed by lines like R1=1.90 (no 'Variables:' header required)

    Output:
    - Multiple .com files, one per step
    - Variables updated for each step
    - scan_summary.txt file listing each file and scanned values
    """

    # === 1. Basic metadata ===
    scan_name = prompt("Enter scan name (e.g., scan1): ").strip() or "scan1"
    input_file = prompt("Enter path to Z-matrix .com file: ", completer=MultiPathCompleter()).strip()
    if not os.path.exists(input_file):
        print("❌ File not found.")
        return

    # ===1.1. Prepare output folder ===
    scan_dir = f"{scan_name}_scan_inputs"
    if os.path.exists(scan_dir):
        print(f"⚠️ Folder '{scan_dir}' already exists.")
        choice = prompt("Do you want to [o]verwrite, [r]ename, or [c]ancel? [o/r/c]: ").strip().lower()
    
        if choice in ['', 'o', 'overwrite']:
            # Overwrite: clear the existing folder
#            import shutil
            try:
                shutil.rmtree(scan_dir)
                print(f"🧹 Removed existing folder '{scan_dir}'.")
            except Exception as e:
                print(f"❌ Failed to remove folder: {e}")
                return
    
        elif choice in ['r', 'rename']:
            new_name = prompt("Enter new scan name: ").strip() or f"{scan_name}_v2"
            scan_dir = f"{new_name}_scan_inputs"
    
        else:
            print("❌ Aborted.")
            return
    
    os.makedirs(scan_dir)
    
    
    summary_lines = []
    step_records = []



    route = prompt("Enter Gaussian route section [# b3lyp/def2TZVP]: ").strip() or "# b3lyp/def2TZVP"
    if not route.startswith("#"):
        route = f"#{route}"

    frozen_vars = []
    if "opt" in route.lower():
        freeze_input = prompt("OPT keyword detected. Enter variables to freeze (comma-separated), or press Enter to skip: ").strip()
        if freeze_input:
            frozen_vars = [v.strip() for v in freeze_input.split(',') if v.strip()]
    
            if "modredundant" or "modred" not in route.lower():
                print("⚠️ Freezing variables requires 'ModRedundant' as part of Opt.")
                add_modred = prompt("Automatically insert it into Opt section? (y/n) [y]: ").strip().lower()
                if add_modred in ["", "y", "yes"]:
                    route = add_modredundant_to_opt(route)
                    print(f"✅ Updated route: {route}")
            
     

    
    # GEN/GENECP handling with @filename reference
    basis_block = ""
    if "gen" in route.lower():
        basis_path = prompt("GEN/GENECP detected. Enter path to basis set file (e.g., def2TZVP.gbs): ",
                            completer=MultiPathCompleter()).strip()
        basis_file = os.path.basename(basis_path)
        if not os.path.exists(basis_path):
            print(f"\n⚠️ File '{basis_path}' not found.")
            proceed = prompt("Do you want to continue anyway and manually add it later? (y/n) [n]: ").strip().lower()
            if proceed not in ["y", "yes"]:
                print("❌ Aborted.")
                return
        basis_block = f"\n@{basis_file}"
        # Auto-copy basis file if it exists
        if os.path.exists(basis_path):
            try:
                copied_path = os.path.join(scan_dir, basis_file)
                shutil.copy2(basis_path, copied_path)
            except Exception as e:
                print(f"⚠️ Failed to copy basis set file: {e}")
        
    
    
    
   # charge = prompt("Enter molecular charge [0]: ").strip() or "0"
   # mult = prompt("Enter multiplicity [1]: ").strip() or "1"
    pairs = []  # list[(charge, multiplicity)]
    
    mode = prompt(
        "Charge/Multiplicity mode:\n"
        "  [1] Single charge + single multiplicity\n"
        "  [2] Multiple charges (same or different multiplicities)\n"
        "  [3] Explicit pairs (e.g., 0/1, -1/2, 1/2)\n"
        "[default: 1]: "
    ).strip() or "1"
    
    if mode == "3":
        raw = prompt("Enter charge/multiplicity pairs (e.g., 0/1, -1/2, 1/2): ").strip()
        for tok in raw.split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                q_s, m_s = tok.split("/", 1)
                q = int(q_s.strip()); m = int(m_s.strip())
                pairs.append((q, m))
            except Exception:
                print(f"[warn] Skipping invalid pair: {tok!r}")
        if not pairs:
            print("[warn] No valid pairs entered; defaulting to 0/1.")
            pairs = [(0, 1)]
    
    elif mode == "2":
        charges = _parse_int_csv(prompt("Enter charges (comma-separated, e.g., 0, -1, 1): ").strip())
        if not charges:
            print("[warn] No charges entered; defaulting to 0.")
            charges = [0]
        same_mult = (prompt("Same multiplicity for all charges? [Y/n]: ").strip().lower() or "y").startswith("y")
        if same_mult:
            m = int(prompt("Multiplicity [default=1]: ").strip() or "1")
            pairs = [(q, m) for q in charges]
        else:
            # try a vector input first
            mults = _parse_int_csv(prompt("Enter multiplicities (comma-separated, same length as charges), or press ENTER to set per charge: ").strip())
            if mults and len(mults) == len(charges):
                pairs = list(zip(charges, mults))
            else:
                # ask per charge
                for q in charges:
                    m = int(prompt(f"Multiplicity for charge {q} [default=1]: ").strip() or "1")
                    pairs.append((q, m))
    
    else:
        q = int(prompt("Charge [default=0]: ").strip() or "0")
        m = int(prompt("Multiplicity [default=1]: ").strip() or "1")
        pairs = [(q, m)]
    
    # === 2. Scan variable definitions ===
    labels = {}  # e.g. 'B1': {'start': 1.9, 'end': 2.1, 'step': 0.05, 'steps': 5, 'values': [...]}

    label_input = prompt("\nEnter variable label(s) to scan (e.g., R1,A1,D1), or press Enter to skip: ").strip()
    if not label_input:
        print("❌ No scan labels provided.")
        return
    
    labels = {}
    for lbl in label_input.split(','):
        lbl = lbl.strip()
        start = safe_float_input(f"  {lbl} start value: ")
        if start is None: return
    
        end = safe_float_input(f"  {lbl} end value: ")
        if end is None: return
    
        step = safe_float_input(f"  {lbl} step size: ")
        if step is None: return
    
        n_steps = int(round((end - start) / step)) + 1
        values = [start + i * step for i in range(n_steps)]
        labels[lbl] = {
            "start": start, "end": end,
            "step": step, "steps": n_steps,
            "values": values
        }
    
    if not labels:
        print("❌ No scan labels provided.")
        return

    # === 3. Prompt for scan mode AFTER collecting variables ===
    if len(labels) > 1:
        print("\nScan mode for multiple variables:")
        print("[1] All variables vary together (default)")
        print("[2] Grid: all combinations")
        print("[3] One-at-a-time")
        mode = prompt("Choice [1/2/3]: ").strip()
        if mode not in ['2', '3']:
            mode = '1'
    else:
        mode = '1'
    
    # === 4. Read input file and split geometry/variables ===
    with open(input_file, 'r') as f:
        lines = f.read().splitlines()

    var_start_index = None
    for i, line in enumerate(lines):
        if '=' in line and len(line.strip().split('=')) == 2:
            var_start_index = i
            break

    if var_start_index is None:
        print("❌ No variable assignments found (e.g., R1=1.90).")
        return

    geom_lines = lines[:var_start_index]
    # Validate that scanned variables appear in the geometry block
    missing_vars = [v for v in labels if not any(v in line for line in geom_lines)]
    if missing_vars:
        print(f"\n⚠️ Warning: These variables do not appear in the Z-matrix: {', '.join(missing_vars)}")
        proceed = prompt("Do you want to continue anyway? (y/n) [n]: ").strip().lower()
        if proceed not in ['y', 'yes']:
            print("❌ Aborted.")
            return
    
    var_lines_original = lines[var_start_index:]

#    # === 5. Prepare output folder ===
#    scan_dir = f"{scan_name}_scan_inputs"
#    os.makedirs(scan_dir, exist_ok=True)
#    summary_lines = []
#    step_records = []

    # === 7. Generate step combinations ===
    if mode == '1':  # Synchronized
        #step_counts = {v['steps'] for v in labels.values()}
        #if len(step_counts) != 1:
        #    print("❌ All variables must have same number of steps in mode 1.")
        #    return
        #n_steps = step_counts.pop()
        step_sizes = {k: v['steps'] for k, v in labels.items()}
        if len(set(step_sizes.values())) != 1:
            print(f"\n⚠️  Variables have different number of steps: {step_sizes}")
            proceed = prompt(f"Proceed using the lowest number of steps ({min(step_sizes.values())})? (y/n) [y]: ").strip().lower()
            if proceed not in ['', 'y', 'yes']:
                print("❌ Aborted.")
                return
            n_steps = min(step_sizes.values())
            for v in labels.values():
                v['values'] = v['values'][:n_steps]
        else:
            n_steps = next(iter(step_sizes.values()))
        
        for i in range(n_steps):
            step_vars = {lbl: v['values'][i] for lbl, v in labels.items()}
            step_records.append((f"{scan_name}_step{i+1:02}", step_vars))

    elif mode == '2':  # Grid (Cartesian product)
        all_keys = list(labels.keys())
        all_values = [labels[k]['values'] for k in all_keys]
        for i, combo in enumerate(itertools.product(*all_values), 1):
            step_vars = dict(zip(all_keys, combo))
            step_records.append((f"{scan_name}_grid{i:03}", step_vars))

    elif mode == '3':  # One-at-a-time
        for lbl, v in labels.items():
            for i, val in enumerate(v['values']):
                step_vars = {k: labels[k]['start'] for k in labels}
                step_vars[lbl] = val
                step_records.append((f"{scan_name}_{lbl}_{i+1:02}", step_vars))

    # === 8. Write files ===
    for name, step_vars in step_records:
        new_var_lines = []
        for line in var_lines_original:
            parts = line.strip().split('=')
            if len(parts) == 2:
                var_name = parts[0].strip()
                if var_name in step_vars:
                    new_var_lines.append(f"{var_name}={step_vars[var_name]:.6f}")
                else:
                    new_var_lines.append(line.strip())
            else:
                new_var_lines.append(line.strip())

        chk_name = f"{name}.chk"
        out_file = os.path.join(scan_dir, f"{name}.com")
        with open(out_file, 'w') as f:
            f.write(f"%chk={chk_name}\n{route}\n\n{name}\n\n{charge} {mult}\n")
            f.write("\n".join(geom_lines).strip() + "\n\n")
            f.write("\n".join(new_var_lines))
        
            if frozen_vars:
                f.write("\n" + "\n".join(f"{v} F" for v in frozen_vars))
        
            if basis_block:
                f.write(basis_block.strip())
        
            f.write("\n")  # Final newline
        
        summary_lines.append(f"{os.path.basename(out_file)}: " +
                             ", ".join(f"{k}={v:.6f}" for k, v in step_vars.items()))

    # === 9. Write scan_summary.txt ===
    summary_file = os.path.join(scan_dir, "scan_summary.txt")
    with open(summary_file, 'w') as f:
        f.write("Generated scan files:\n\n")
        f.write("\n".join(summary_lines))
        f.write("\n\nScan setup metadata:\n")
        f.write(f"Route: {route}\n")
        f.write(f"Charge: {charge}, Multiplicity: {mult}\n")
        f.write(f"Scan Mode: {mode}\n")
        f.write("Scanned Variables:\n")
        for k, v in labels.items():
            f.write(f"  {k}: start={v['start']}, end={v['end']}, step={v['step']}, steps={v['steps']}\n")
        if basis_block:
            f.write(f"Basis set reference: {basis_block.strip()}\n")
    
    
    print(f"\n✅ Generated {len(step_records)} input files in {scan_dir}")
    print(f"📝 Summary written to {summary_file}")



