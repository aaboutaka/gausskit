import os

def write_pimom_input(base_log, alpha_swaps, beta_swaps, charge, multiplicity,
                      method, footer=None, include_func_in_name=True, custom_oldchk=None):
    base_name = os.path.splitext(base_log)[0]
    oldchk = custom_oldchk if custom_oldchk else base_name + ".chk"

    suffix = ""
    if alpha_swaps:
        suffix += "-a" + "-".join("_".join(pair) for pair in alpha_swaps)
    if beta_swaps:
        suffix += "-b" + "-".join("_".join(pair) for pair in beta_swaps)
    if include_func_in_name:
        suffix += f"-{method}"

    outchk = base_name + suffix + ".chk"
    comfile = base_name + suffix + ".com"

    with open(comfile, "w") as f:
        f.write(f"%oldchk={oldchk}\n")
        f.write(f"%chk={outchk}\n")
        f.write(f"#p {method} scf=(novaracc,pimom,fermi,novaracc) integral=SuperFineGrid guess=(alter,read) geom=check chkbasis int=noxctest\n\n")
        f.write("Title Card Required\n\n")
        f.write(f"{charge} {multiplicity}\n\n")

        for pair in alpha_swaps:
            f.write(" ".join(pair) + " ! alpha swap\n")
        if alpha_swaps and beta_swaps:
            f.write("\n")
        for pair in beta_swaps:
            f.write(" ".join(pair) + " ! beta swap\n")

        f.write("\n\n")
        if footer:
            f.write(f"@{footer}\n")

    print(f"\n✅ Created file: {comfile}")
    print(f"   → Using %oldchk: {oldchk}")
    print(f"   → Output %chk  : {outchk}")



