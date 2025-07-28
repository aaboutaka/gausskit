import os

# in builder.py

def write_pimom_input(
    base_log,
    alpha_swaps,
    beta_swaps,
    charge,
    multiplicity,
    method,
    footer=None,
    include_func_in_name=True,
    custom_oldchk=None,
    include_optfreq=False,    # <— new flag
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



#def write_pimom_input(
#    base_log,
#    alpha_swaps,
#    beta_swaps,
#    charge,
#    multiplicity,
#    method,
#    footer=None,
#    include_func_in_name=True,
#    custom_oldchk=None
#):
#    """
#    Generates a Gaussian .com file performing PIMOM swaps.
#    Alpha swaps go first; beta swaps are preceded by one blank line
#    if alpha_swaps exist, or two blank lines if beta-only.
#    """
#    # 1) Determine base name and checkpoint names
#    base_name = os.path.splitext(base_log)[0]
#    oldchk = custom_oldchk if custom_oldchk else base_name + ".chk"
#
#    # 2) Build suffix for file names
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
#    # 3) Write the .com
#    with open(comfile, "w") as f:
#        # header
#        f.write(f"%oldchk={oldchk}\n")
#        f.write(f"%chk={outchk}\n")
#        f.write(
#            f"#p {method} scf=(novaracc,pimom,fermi,novaracc) "
#            "integral=SuperFineGrid guess=(alter,read) "
#            "geom=check chkbasis int=noxctest\n\n"
#        )
#        f.write("Title Card Required\n\n")
#
#        # charge / multiplicity + one blank line
#        f.write(f"{charge} {multiplicity}\n\n")
#
#        # alpha swaps (if any)
#        for pair in alpha_swaps:
#            f.write(" ".join(pair) + " ! alpha swap\n")
#
#        # beta swaps (if any), with the correct blank‐line logic
#        if beta_swaps:
#            if alpha_swaps:
#                # one blank line between α and β
#                f.write("\n")
#            else:
#                # two blank lines if β‐only
#                f.write("\n\n")
#            for pair in beta_swaps:
#                f.write(" ".join(pair) + " ! beta swap\n")
#
#        # final blank space + optional footer
#        f.write("\n\n")
#        if footer:
#            f.write(f"@{footer}\n")
#
#    # 4) Print confirmation
#    print(f"\n✅ Created file: {comfile}")
#    print(f"   → Using %oldchk: {oldchk}")
#    print(f"   → Output %chk  : {outchk}")


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
#        f.write(f"#p {method} scf=(pimom,fermi,novaracc) integral=SuperFineGrid guess=(alter,read) geom=check chkbasis \n\n")
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
#


