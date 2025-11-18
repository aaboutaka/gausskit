# gausskit/regenerator.py
import os
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from gausskit.completions import tab_autocomplete_prompt


# =====================================================================
#  CANONICAL FUNCTIONAL LIST
# =====================================================================
DFT_FUNCTIONALS = [
    'HF', 'BLYP', 'PBEPBE', 'PBE1PBE', 'TPSSh',
    'B3LYP', 'B3P86', 'B3PW91', 'O3LYP',
    'APFD', 'APF', 'wB97XD',
    'LC-wHPBE', 'LC-wPBE', 'CAM-B3LYP', 'wB97X', 'wB97',
    'MN15', 'M11', 'SOGGA11X', 'N12SX', 'MN12SX',
    'PW6B95', 'PW6B95D3', 'M08HX',
    'M06', 'M06HF', 'M062X', 'M05', 'M052X',
    'HSEH1PBE', 'OHSE2PBE', 'OHSE1PBE', 'PBEh1PBE',
    'B1B95', 'B1LYP', 'mPW1PW91', 'mPW1LYP', 'mPW1PBE', 'mPW3PBE',
    'B98', 'B971', 'B972',
    'tHCTHhyb', 'BMK',
    'X3LYP', 'HISSbPBE',
    'BHandH', 'BHandHLYP',
    'PW91', 'mPW', 'G96', 'O', 'TPSS', 'RevTPSS', 'BRx', 'PKZB', 'wPBEh', 'PBEh',
    'VWN', 'VWN5', 'LYP', 'PL', 'P86', 'B95',
    'KCIS', 'BRC',
    'VP86', 'V5LYP',
    'VSXC', 'HCTH', 'HCTH93', 'HCTH147', 'HCTH407', 'tHCTH',
    'B97D', 'B97D3',
    'M06L', 'SOGGA11', 'M11L', 'MN12L', 'N12', 'MN15L'
]

# Lowercase lookup
DFT_FUNC_SET = {f.lower(): f for f in DFT_FUNCTIONALS}

DEBUG_FUNCTIONAL = False


def _dbg(msg: str):
    if DEBUG_FUNCTIONAL:
        print(msg)


# =====================================================================
#   FUNCTIONAL EXTRACTION FROM FILENAME
# =====================================================================
def extract_functional_from_filename(fname: str) -> str:
    """
    Detect functional from filename tokens:
    e.g. L3_mF_H_product_wB97XD_aug-cc-pVTZ_q1_m1.com → wB97XD
    """
    low = fname.lower()
    tokens = low.replace("-", "_").split("_")

    for t in tokens:
        if t in DFT_FUNC_SET:
            return DFT_FUNC_SET[t]
        if t.lower() in DFT_FUNC_SET:
            return DFT_FUNC_SET[t.lower()]

    return ""


# =====================================================================
#   ROUTE EXTRACTION FROM .COM FILE
# =====================================================================
def extract_route_from_com_file(path: str) -> str:
    with open(path, "r") as f:
        for line in f:
            s = line.strip()
            if s.startswith("#"):
                return s.lstrip("#").strip()
    return ""


# =====================================================================
#   FUNCTIONAL EXTRACTION FROM ROUTE
# =====================================================================
def extract_functional_from_route(route_raw: str) -> str:

    _dbg("\n[DEBUG] ========================================")
    _dbg(f"[DEBUG] Route raw: {route_raw!r}")

    if not route_raw:
        _dbg("[DEBUG] No route → ''")
        return ""

    low = route_raw.lower()
    _dbg(f"[DEBUG] Route lower: {low!r}")

    tokens = low.replace("=", " ").replace("/", " ").split()
    _dbg(f"[DEBUG] Tokens: {tokens}")

    # 1) First token
    first = tokens[0]
    if first in DFT_FUNC_SET:
        func = DFT_FUNC_SET[first]
        _dbg(f"[DEBUG] MATCH first token → {func}")
        return func

    # 2) Slash form
    if "/" in route_raw:
        cand = low.split("/")[0].strip()
        if cand in DFT_FUNC_SET:
            func = DFT_FUNC_SET[cand]
            _dbg(f"[DEBUG] MATCH slash → {func}")
            return func

    # 3) Scan all tokens
    for t in tokens:
        if t.lower() in DFT_FUNC_SET:
            func = DFT_FUNC_SET[t.lower()]
            _dbg(f"[DEBUG] MATCH scan → {func}")
            return func

    _dbg("[DEBUG] *** NO MATCH FOUND ***")
    return ""


# =====================================================================
#   MASTER FUNCTIONAL SELECTOR
# =====================================================================
def determine_functional(path: str, use_old: bool, manual: str = "") -> str:

    fname = os.path.basename(path)

    if use_old:
        # filename first
        func = extract_functional_from_filename(fname)
        if func:
            _dbg(f"[DEBUG] Functional found in filename: {func}")
            return func

        # route line next
        route = extract_route_from_com_file(path)
        _dbg(f"[DEBUG] Extracted route: {route!r}")

        func = extract_functional_from_route(route)
        if func:
            _dbg(f"[DEBUG] Functional found in route: {func}")
            return func

        _dbg("[DEBUG] No functional found.")
        return ""

    else:
        manual_clean = manual.strip().split()[0] if manual.strip() else ""
        _dbg(f"[DEBUG] Using manual functional: {manual_clean}")
        return manual_clean


# =====================================================================
#   REGENERATOR MAIN
# =====================================================================
def generate_regenerated_inputs():
    """
    Batch-regenerate Gaussian inputs for all .com/.gjf files.
    Now supports automatic functional extraction from filename or route.
    """

    print("\n=== Batch Gaussian Input Regenerator ===")

    input_files = [f for f in os.listdir()
                   if f.lower().endswith((".com", ".gjf"))]

    if not input_files:
        print("❌ No .com or .gjf files found.")
        return

    print(f"Found {len(input_files)} input file(s).")

    ans = prompt("Generate inputs for ALL files? [Y/n]: ").strip().lower()
    if ans.startswith("n"):
        sel = tab_autocomplete_prompt(
            "Select file: ",
            completer=WordCompleter(input_files)
        ).strip()
        input_files = [sel]

    # Functional extraction mode
    ans = prompt("Extract functional from original .com files? [Y/n]: ").strip().lower()
    use_old = (ans == "" or ans.startswith("y"))

    manual_func = ""
    if not use_old:
        manual_func = prompt("Enter functional manually: ").strip()

    # Route
    route_raw = prompt("Enter Gaussian route line (without #): ").strip()

    # Stability check condition
    wants_stability = any(w in route_raw.lower() for w in ("opt", "freq"))

    # Prefix
    prefix = prompt("Enter prefix for new %chk files: ").strip()
    if not prefix:
        prefix = "NEW"

    # ChkBasis: DEFAULT = YES
    ans = prompt(
        "Add ChkBasis (reuse basis from checkpoint)? [Y/n]: "
    ).strip().lower()
    add_chkbasis = (ans == "" or ans.startswith("y"))

    # ----------------------------------------------------------
    # PROCESS EACH INPUT FILE
    # ----------------------------------------------------------
    for infile in input_files:

        base = os.path.splitext(infile)[0]
        oldchk = f"{base}.chk"
        newchk = f"{base}_{prefix}.chk"
        newname = f"{base}_{prefix}.com"

        print(f"\n=== Processing {infile} ===")

        # determine functional
        functional = determine_functional(
            path=infile,
            use_old=use_old,
            manual=manual_func
        )

        if not functional:
            print("⚠ Functional not found; stability link will be generic.")

        # WRITE NEW FILE
        with open(newname, "w") as f:

            # main job header
            f.write(f"%oldchk={oldchk}\n")
            f.write(f"%chk={newchk}\n")

            extra = " chkbasis" if add_chkbasis else ""
            # Keep your ordering: user route then functional
            f.write(f"#p {route_raw} {functional} geom=allcheck guess=read{extra}\n\n")

            f.write(f"{base} regenerated input\n\n\n")

            # stability link
            if wants_stability:
                stabchk = f"{base}_{prefix}_stab.chk"

                f.write("--Link1--\n")
                f.write(f"%oldchk={newchk}\n")
                f.write(f"%chk={stabchk}\n")

                f.write(
                    f"#p {functional} stable=opt guess=read geom=allcheck "
                    f"chkbasis int=superfinegrid\n\n"
                )

        print(f"✅ Wrote: {newname}")

    print("\n🎉 All files generated.")

