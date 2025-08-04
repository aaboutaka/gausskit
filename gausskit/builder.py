import os

# in builder.py

def write_pimom_input(
    base_log,
    alpha_swaps,
    beta_swaps,
    charge,
    multiplicity,
    method,
    add_noxctest= False,
    footer=None,
    include_func_in_name=True,
    custom_oldchk=None,
    include_optfreq=False,
    suffix_tag=""):
    """
    Generates a Gaussian .com file performing PIMOM swaps.
    If include_optfreq is True, prepends 'Opt Freq' to the route
    and appends '-opt' to the filename.
    """
    # 1) Base names
    base_name = os.path.splitext(base_log)[0]
    oldchk    = custom_oldchk or f"{base_name}.chk"

    # 2) Build filename suffix
    suffix = ""
    if include_optfreq:
        suffix += "-opt"
    if alpha_swaps:
        suffix += "-a" + "-".join("_".join(pair) for pair in alpha_swaps)
    if beta_swaps:
        suffix += "-b" + "-".join("_".join(pair) for pair in beta_swaps)
    if include_func_in_name:
        suffix += f"-{method}"

    outchk  = f"{base_name}{suffix}.chk"
    comfile = f"{base_name}{suffix}.com"

    # 3) Build route line
    route = method
    if include_optfreq:
        route += " Opt Freq"
    route += " scf=(pimom,fermi,novaracc)"
    route += " integral=SuperFineGrid guess=(alter,read) geom=check chkbasis"
    if add_noxctest:
        route += " int=noxctest"


    # 4) Write .com
    with open(comfile, "w") as f:
        f.write(f"%oldchk={oldchk}\n")
        f.write(f"%chk={outchk}\n")
        f.write(f"#p {route}\n\n")
        f.write("Title Card Required\n\n")
        f.write(f"{charge} {multiplicity}\n\n")

        # alpha swaps
        for p in alpha_swaps:
            f.write(" ".join(p) + " ! alpha swap\n")

        # beta swaps, with correct spacing
        if beta_swaps:
            f.write("\n" if alpha_swaps else "\n")
            for p in beta_swaps:
                f.write(" ".join(p) + " ! beta swap\n")

        f.write("\n\n")
        if footer:
            f.write(f"@{footer}\n")

    # 5) Confirmation
    print(f"\n✅ Created file: {comfile}")
    print(f"   → Using %oldchk: {oldchk}")
    print(f"   → Output %chk  : {outchk}")



