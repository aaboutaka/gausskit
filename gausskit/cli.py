import os
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from .io import is_gaussian_terminated, extract_homo_lumo_indices
from .utils import parse_swap_pairs
from .builder import write_pimom_input
import sys

def main():
    if '--about' in sys.argv:
        print_about()
        return
    if '--help' in sys.argv:
        print_help()
        return
    if '--version' in sys.argv:
        print("GaussKit version 0.1.0")
        return

    print("=" * 70)
    print("Welcome to GaussKit: Gaussian Input Automation Toolkit")
    print("Author: Ali Abou Taka (aka Qathota)")
    print("Type `gaussjob --about` for full details.")
    print("=" * 70)

    choice = prompt("Choose mode: [1] PIMOM Swap  [2] Input Generator : ").strip()
    if choice == "2":
        from .generator import create_gaussian_input
        create_gaussian_input()
    else:
        from .cli import run_pimom_cli
        run_pimom_cli()

def print_about():
    print("""
🧪 GaussKit - Gaussian Input Generation & Orbital Manipulation Toolkit
Author: Ali Abou Taka (aka Qathota) | GitHub: @aaboutaka
Email: abotaka.ali@gmail.com

Features:
- PIMOM orbital swap .com file generator
- Custom route line input with auto-complete
- Flexible .xyz parsing (comma/tab/space/indexed)
- Optional stability job via Link1 or separate file
- Optional @footer basis support
- Command-line interactive mode with validation

Usage:
    gaussjob             Launch the interactive CLI
    gaussjob --about     Print this description
    gaussjob --help      Show usage instructions
    gaussjob --version   Show version number

Project Repository:
    https://github.com/aaboutaka/gausskit
""")

def print_help():
    print("""
Usage: gaussjob [--about | --help | --version]

No arguments        Start interactive CLI
--about             Show package overview, features, and author info
--help              Show usage summary
--version           Show installed version of GaussKit

After launch:
    [1] PIMOM Swap          → generate excited state input files
    [2] Input Generator     → create ground/stability job inputs

Documentation: https://github.com/aaboutaka/gausskit
""")




def run_pimom_cli():
    print("=" * 75)
    print("📍 This script sets up follow-up Gaussian jobs using PIMOM.")
    print("    - Verifies Gaussian normal termination before proceeding.")
    print("    - Extracts HOMO/LUMO indices from a .log file.")
    print("    - Prompts for alpha/beta orbital swaps.")
    print("    - Supports automatic HOMO-n ↔ LUMO permutations.")
    print("    - Optionally adds method name to output filename.")
    print("=" * 75)

    log_completer = WordCompleter([f for f in os.listdir() if f.endswith('.log')])
    logfile = prompt("Enter the Gaussian log file: ", completer=log_completer).strip()

    if not os.path.exists(logfile):
        print(f"❌ Log file '{logfile}' not found.")
        return

    if not is_gaussian_terminated(logfile):
        print("⚠️ WARNING: This file did NOT terminate normally.")
        cont = prompt("Do you want to continue anyway? [y/n]: ").strip().lower()
        if cont != 'y':
            print("Aborted.")
            return

    info = extract_homo_lumo_indices(logfile)
    print("\n→ HOMO/LUMO information extracted:")
    for k, v in info.items():
        print(f"   {k:<12}: {v}")

    alpha_input = prompt("\nEnter alpha orbital swaps (e.g., 77 78, 76 79), or press ENTER to skip: ").strip()
    beta_input = prompt("Enter beta orbital swaps (e.g., 81 82, 80 83), or press ENTER to skip: ").strip()
    charge = prompt("Enter charge (default = 0): ").strip() or "0"
    multiplicity = prompt("Enter multiplicity (default = 1): ").strip() or "1"
    method = prompt("Enter method (default = uwb97xd): ").strip() or "uwb97xd"
    include_func = prompt("Include method in output filename? [y/n]: ").strip().lower() == 'y'
    footer = prompt("Enter footer file to reference (e.g., SDDPlusTZ.gbs), or press ENTER to skip: ").strip() or None

    custom_oldchk = None
    if prompt("Use different %oldchk than log base name? [y/n]: ").strip().lower() == 'y':
        custom_oldchk = prompt("Enter full path or name for %oldchk file: ").strip()

    alpha_pairs = parse_swap_pairs(alpha_input)
    beta_pairs = parse_swap_pairs(beta_input)

    auto_alpha = prompt("Auto-generate alpha HOMO-n ↔ LUMO permutations? [y/n]: ").strip().lower() == 'y'
    auto_beta = prompt("Auto-generate beta HOMO-n ↔ LUMO permutations? [y/n]: ").strip().lower() == 'y'
    combine = prompt("Combine alpha and beta permutations in the same file? [y/n]: ").strip().lower() == 'y'

    if combine:
        count = int(prompt("  → How many HOMO-n permutations for alpha and beta? (e.g., 3): ").strip())
        for i in range(count):
            a_pair = [str(info["homo_alpha"] - i), str(info["lumo_alpha"])]
            b_pair = [str(info["homo_beta"] - i), str(info["lumo_beta"])]
            write_pimom_input(logfile, [a_pair], [b_pair], charge, multiplicity, method, footer, include_func, custom_oldchk)
    else:
        if auto_alpha:
            count = int(prompt("  → How many alpha permutations to generate? e.g., 3: ").strip())
            for i in range(count):
                a_pair = [str(info["homo_alpha"] - i), str(info["lumo_alpha"])]
                write_pimom_input(logfile, [a_pair], [], charge, multiplicity, method, footer, include_func, custom_oldchk)

        if auto_beta:
            count = int(prompt("  → How many beta permutations to generate? e.g., 2: ").strip())
            for i in range(count):
                b_pair = [str(info["homo_beta"] - i), str(info["lumo_beta"])]
                write_pimom_input(logfile, [], [b_pair], charge, multiplicity, method, footer, include_func, custom_oldchk)

    if alpha_pairs or beta_pairs:
        write_pimom_input(logfile, alpha_pairs, beta_pairs, charge, multiplicity, method, footer, include_func, custom_oldchk)

if __name__ == "__main__":
    main()


