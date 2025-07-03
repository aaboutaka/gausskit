def is_gaussian_terminated(filepath, lines_to_check=30):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            tail = f.readlines()[-lines_to_check:]
        return any("Normal termination of Gaussian" in line for line in tail)
    except Exception as e:
        print(f"⚠️ Error checking termination in {filepath}: {e}")
        return False

def extract_homo_lumo_indices(logfile):
    with open(logfile, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    alpha_occup, beta_occup = [], []
    for line in lines:
        if "Alpha  occ. eigenvalues" in line:
            alpha_occup += [float(x) for x in line.split('--')[-1].split()]
        elif "Alpha virt. eigenvalues" in line:
            break

    for line in lines:
        if "Beta  occ. eigenvalues" in line:
            beta_occup += [float(x) for x in line.split('--')[-1].split()]
        elif "Beta virt. eigenvalues" in line:
            break

    return {
        "homo_alpha": len(alpha_occup),
        "lumo_alpha": len(alpha_occup) + 1,
        "homo_beta": len(beta_occup),
        "lumo_beta": len(beta_occup) + 1,
    }


