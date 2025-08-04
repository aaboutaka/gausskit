#!/usr/bin/env python3
import os
import sys
from itertools import product
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from gausskit.utils import HybridCompleter
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

