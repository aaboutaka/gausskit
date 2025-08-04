#!/usr/bin/env python3
import os
import sys
from itertools import product
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from gausskit.utils import HybridCompleter
from gausskit.utils import MultiPathCompleter
from .utils import prompt_and_submit


from prompt_toolkit.completion import PathCompleter

from .io import is_gaussian_terminated, extract_homo_lumo_indices
from .utils import parse_swap_pairs
from .builder import write_pimom_input
from .franck_condon import generate_fc_input
from .scheduler import run_job_scheduler
from .analyze import run_log_analyzer
from .generator import (
    create_gaussian_input,
    create_benchmark_inputs,
    extract_xyz_from_log,
    extract_xyz_cli  
)



def print_about():
    print("""
🧪 GaussKit - Gaussian Input Generation & Automation Toolkit
Author: Ali Abou Taka | GitHub: @aaboutaka
Email: abotaka.ali@gmail.com

Features:
 - PIMOM Swap                         (pimom, swap, 1)
 - Ground‐state Input Generator       (input, generate, 2)
 - Franck–Condon Input Generator      (fc, franck, 3)
 - Job Scheduler                      (schedule, scheduler, 4)
 - Benchmark Input Generator          (benchmark, 5)
 - Log Analyzer                       (analyze, 6)
 - Vibronic Summary Tool              (vibronic, 7)
 - Interactive menu                   (no args)
 - Meta flags: --about, --help, --version
""".strip())

def print_help():
    print("""
Usage: gausskit [subcommand] [options]

Meta flags:
  --about        Show overview
  --help         Show this help
  --version      Print version

Subcommands:
  pimom, swap, 1       PIMOM orbital swap
  input, generate, 2   Ground‐state input generator
  fc, franck, 3        Franck–Condon input generator
  schedule, 4          Job Scheduler
  benchmark, 5         Benchmark input generator
  analyze, 6           Log Analyzer CLI
  vibronic, 7          Vibronic summary & plotting

No args: interactive menu.
""".strip())



def run_pimom_cli():
    import os
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter
    from .io import is_gaussian_terminated, extract_homo_lumo_indices
    from .utils import parse_swap_pairs
    from .builder import write_pimom_input

    # 1) Header
    print("=" * 75)
    print("📍 This script sets up follow-up Gaussian jobs using PIMOM.")
    print("    - Verifies Gaussian normal termination before proceeding.")
    print("    - Extracts HOMO/LUMO indices from a .log file.")
    print("    - Prompts for alpha/beta orbital swaps.")
    print("    - Supports automatic HOMO-n ↔ LUMO permutations.")
    print("    - Optionally adds method name to output filename.")
    print("    - Now supports Opt+Freq in route (none/yes/both).")
    print("=" * 75)

    # 2) Choose .log file
    log_completer = WordCompleter([f for f in os.listdir() if f.endswith('.log')])
    logfile = prompt("Enter the Gaussian log file: ", completer=log_completer).strip()
    if not os.path.exists(logfile):
        print(f"❌ Log file '{logfile}' not found.")
        return

    # 3) Check normal termination
    if not is_gaussian_terminated(logfile):
        cont = prompt("⚠️ This file did NOT terminate normally. Continue anyway? [y/N]: ").strip().lower() or "n"
        if not cont.startswith('y'):
            print("Aborted.")
            return

    # 4) Extract HOMO/LUMO
    info = extract_homo_lumo_indices(logfile)
    print("\n→ HOMO/LUMO indices:")
    for k, v in info.items():
        print(f"   {k:<12}: {v}")

    # 5) Opt+Freq choice
    opt_choice = prompt("Opt+Freq route? [0] none  [1] yes  [2] both [default: 0]: ").strip() or "0"
    while opt_choice not in ("0", "1", "2"):
        opt_choice = prompt("Please enter 0, 1, or 2 [default: 0]: ").strip() or "0"

    # 5-b Ask about skipping quadrature test
    add_noxctest = prompt("Add 'int=noxctest' to PIMOM route section to avoid quadrature errors? [y/N]: ").strip().lower().startswith("y")

    # 6) Manual swap inputs & settings
    alpha_input  = prompt("\nAlpha swaps (e.g. 77 78,76 79) or ENTER to skip: ").strip()
    beta_input   = prompt("Beta swaps  (e.g. 81 82,80 83) or ENTER to skip: ").strip()
    charge       = prompt("Charge [default: 0]: ").strip() or "0"
    multiplicity = prompt("Multiplicity [default: 1]: ").strip() or "1"
    method       = prompt("Method [default: uwb97xd]: ").strip() or "uwb97xd"

    ans = prompt("Include method in filename? [y/N]: ").strip().lower() or "n"
    include_func = ans.startswith("y")
    footer = prompt("Footer file (e.g. SDDPlusTZ.gbs) or ENTER to skip: ",
            completer=MultiPathCompleter(file_filter=lambda f: f.endswith('.gbs') or f.endswith('.txt'))).strip() or None


    ans = prompt("Use custom %oldchk? [y/N]: ").strip().lower() or "n"
    custom_oldchk = prompt("  → Enter %oldchk path: ").strip() if ans.startswith("y") else None

    alpha_pairs = parse_swap_pairs(alpha_input)
    beta_pairs  = parse_swap_pairs(beta_input)

    # 7) Auto / combine options
    auto_alpha = prompt("Auto-generate alpha permutations? [y/N]: ").strip().lower().startswith('y') or False
    auto_beta  = prompt("Auto-generate beta permutations? [y/N]: ").strip().lower().startswith('y') or False
    combine    =  False

    # 8) Writer wrapper that handles opt_choice
    def do_write(a_swaps, b_swaps, charge, multiplicity):
        # always write the 'none' version
        write_pimom_input(
            logfile, a_swaps, b_swaps,
            charge, multiplicity,
            method, add_noxctest, footer, include_func, custom_oldchk,
            include_optfreq=False
        )
        # if 'yes' overwrite that file with Opt+Freq
        if opt_choice == "1":
            write_pimom_input(
                logfile, a_swaps, b_swaps,
                charge, multiplicity,
                method, add_noxctest, footer, include_func, custom_oldchk,
                include_optfreq=True
            )
        # if 'both', append second file with Opt+Freq
        elif opt_choice == "2":
            write_pimom_input(
                logfile, a_swaps, b_swaps,
                charge, multiplicity,
                method, add_noxctest, footer, include_func, custom_oldchk,
                include_optfreq=True
            )

    # 9) Handle the different combinations
    # multiple α-swaps + multiple β-swaps
    if len(alpha_pairs) > 1 or len(beta_pairs) > 1 and not (auto_alpha or auto_beta):
        choice = prompt(
            "Detected multiple α-swaps and multiple β-swaps.\n"
            "  [1] Pair each α with each β (cross-product)\n"
            "  [2] Combine ALL α & β in one file\n"
            "  [3] One file per α (each α with ALL β)\n"
            "  [4] One file per β (each β with ALL α)\n"
            "[default: 1]: "
        ).strip() or "1"

        if choice == "2":
            combine = True
            # one file with all α's and all β's
            do_write(alpha_pairs, beta_pairs, charge, multiplicity)

        elif choice == "1":
            # one file per (α,β) pair
            for a in alpha_pairs:
                for b in beta_pairs:
                    do_write([a], [b], charge, multiplicity)

        elif choice == "3":
            # one file per α, pairing that α with all β's
            for a in alpha_pairs:
                do_write([a], beta_pairs, charge, multiplicity)

        elif choice == "4":
            # one file per β, pairing that β with all α's
            for b in beta_pairs:
                do_write(alpha_pairs, [b], charge, multiplicity)

        else:
            # fallback to combine all
            print("Invalid choice — defaulting to combine all.")
            do_write(alpha_pairs, beta_pairs, charge, multiplicity)

        return

    # 9a) If both manual α & β and no auto/combine flags, ask how to split
    if alpha_pairs and beta_pairs and not (auto_alpha or auto_beta or combine):
        # ask α-split
        sep = prompt(
            "Multiple α-swaps detected. Combine all α-swaps or separate per-swap? [1=combine/2=separate, default=1]: "
        ).strip() or "1"
        # ask β-split
        bep = prompt(
            "Multiple β-swaps detected. Combine all β-swaps or separate per-swap? [1=combine/2=separate, default=1]: "
        ).strip() or "1"

        # same multiplicity?
        samem = prompt("Same multiplicity for both α/β? [Y/n]: ").strip().lower() or "y"
        same_mult = samem.startswith("y")

        # split α
        if sep == "2":
            for p in alpha_pairs:
                m = multiplicity if same_mult else prompt(f"Multiplicity for α-swap {p} [default={multiplicity}]: ").strip() or multiplicity
                do_write([p], [], charge, m)
        else:
            do_write(alpha_pairs, [], charge, multiplicity)

        # split β
        if bep == "2":
            for p in beta_pairs:
                m = multiplicity if same_mult else prompt(f"Multiplicity for β-swap {p} [default={multiplicity}]: ").strip() or multiplicity
                do_write([], [p], charge, m)
        else:
            do_write([], beta_pairs, charge, multiplicity)

        return

    # 9b) α-only manual
    if alpha_pairs and not beta_pairs and not (auto_alpha or combine):
        if len(alpha_pairs) > 1:
            one_or_sep = prompt("Multiple α-swaps: one file or separate? [1=one/2=sep, default=1]: ").strip() or "1"
            if one_or_sep == "2":
                for p in alpha_pairs:
                    do_write([p], [], charge, multiplicity)
            else:
                do_write(alpha_pairs, [], charge, multiplicity)
        else:
            do_write(alpha_pairs, [], charge, multiplicity)
        return

    # 9c) β-only manual
    if beta_pairs and not alpha_pairs and not (auto_beta or combine):
        if len(beta_pairs) > 1:
            one_or_sep = prompt("Multiple β-swaps: one file or separate? [1=one/2=sep, default=1]: ").strip() or "1"
            if one_or_sep == "2":
                for p in beta_pairs:
                    do_write([], [p], charge, multiplicity)
            else:
                do_write([], beta_pairs, charge, multiplicity)
        else:
            do_write([], beta_pairs, charge, multiplicity)
        return

    # 9d) Combine α+β
    if combine:
        cnt = int(prompt("How many α/β permutations? [default=1]: ").strip() or "1")
        for i in range(cnt):
            a = [str(info["homo_alpha"] - i), str(info["lumo_alpha"])]
            b = [str(info["homo_beta"]  - i), str(info["lumo_beta"])]
            do_write(a, b, charge, multiplicity)
        return

    # 9e) Auto-alpha
    if auto_alpha:
        cnt = int(prompt("α-permutations count? [default=1]: ").strip() or "1")
        for i in range(cnt):
            p = [str(info["homo_alpha"] - i), str(info["lumo_alpha"])]
            do_write(p, [], charge, multiplicity)

    # 9f) Auto-beta
    if auto_beta:
        cnt = int(prompt("β-permutations count? [default=1]: ").strip() or "1")
        for i in range(cnt):
            p = [str(info["homo_beta"] - i), str(info["lumo_beta"])]
            do_write([], p, charge, multiplicity)

    # 9g) Fallback if any manual pairs left
    if alpha_pairs or beta_pairs:
        do_write(alpha_pairs, beta_pairs, charge, multiplicity)


def main():
    # --- 1) Direct‐call subcommands ---
    if len(sys.argv) >= 2:
        cmd = sys.argv[1].lower()

        if cmd in ("pimom", "swap", "1"):
            from .cli import run_pimom_cli
            run_pimom_cli()
            return

        if cmd in ("input", "generate", "2"):
            create_gaussian_input()
            return

        if cmd in ("fc", "franck", "3"):
            generate_fc_input()
            return

        if cmd in ("schedule", "scheduler", "4"):
            run_job_scheduler()
            return

        if cmd in ("benchmark", "5"):
            create_benchmark_inputs()
            return

        if cmd in ("analyze", "6"):
            logfile = sys.argv[2] if len(sys.argv) > 2 else None
            run_log_analyzer(logfile)
            return

        if cmd in ("vibronic", "7"):
            # remove the subcommand token so vib_main() sees only its flags/logfiles
            sys.argv.pop(1)
            from gausskit.vibronic import main as vib_main
            return vib_main()

        if cmd in ("extract", "8"):
            sys.argv.pop(1)
            from gausskit.generator import extract_xyz_cli
            return extract_xyz_cli()
     
        if cmd in ("compare", "9"):
            sys.argv.pop(1)
            from .analyze import compare_log_energies
            return compare_log_energies()


        if cmd in ("handle", "10"):
            sys.argv.pop(1)
            from gausskit.error_fixer import batch_fix_and_report
            return batch_fix_and_report() 


        # Meta flags
        if cmd in ("--about", "about"):
            print_about()
            return
        if cmd in ("--help", "help"):
            print_help()
            return
        if cmd in ("--version", "version"):
            print("GaussKit version 0.1.0")
            return



    # --- 2) Interactive menu (fallback) ---
    if "--about" in sys.argv:
        print_about()
        return
    if "--help" in sys.argv:
        print_help()
        return
    if "--version" in sys.argv:
        print("GaussKit version 0.1.0")
        return

    print("=" * 70)
    print("Welcome to GaussKit: Gaussian Input Automation Toolkit")
    print("Author: Ali Abou Taka")
    print("Type `gausskit --about` for full details.")
    print("=" * 70)

    choice = prompt(
        "Choose mode:\n"
        "[0] Exit\n"
        "[1] PIMOM Swap\n"
        "[2] Input Generator\n"
        "[3] Franck–Condon Input Generator\n"
        "[4] Job Scheduler\n"
        "[5] Benchmark Input Generator\n"
        "[6] Log Analyzer CLI\n"
        "[7] Vibronic Summary Tool\n"
        "[8] Extract XYZ From Log files\n"
        "[9] Energy Comparison for Benchmark Logs\n"
        "[10] Error Handler\n"
        "Enter your choice [0–10]: "
    ).strip()

    if choice == "0":
        print("Exiting GaussKit.")
        return
    elif choice == "1":
        from .cli import run_pimom_cli
        run_pimom_cli()
    elif choice == "2":
        create_gaussian_input()
    elif choice == "3":
        generate_fc_input()
    elif choice == "4":
        run_job_scheduler()
    elif choice == "5":
        create_benchmark_inputs()
    elif choice == "6":
        run_log_analyzer()
    elif choice == "7":
        from gausskit.vibronic import main as vib_main
        vib_main()
    elif choice == "8":
        from .generator import extract_xyz_cli as run_xyz_extractor
        run_xyz_extractor()
    elif choice == "9":
        from .analyze import compare_log_energies
        compare_log_energies()
    elif choice == "10":  
        from gausskit.error_fixer import batch_fix_and_report
        batch_fix_and_report()


    
    else:
        print("❌ Invalid choice, exiting.")

if __name__ == "__main__":
    main()

