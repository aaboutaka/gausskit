import os
from gausskit.completions import tab_autocomplete_prompt
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

def generate_fc_input():
    print("=" * 60)
    print("Franck–Condon Input Generator (Gaussian)")
    print("=" * 60)

    chk_completer = WordCompleter([f for f in os.listdir() if f.endswith('.chk')])

    oldchk = prompt("Enter Initial checkpoint filename: ", completer=chk_completer).strip()
    newchk = prompt("Enter Final checkpoint filename: ", completer=chk_completer).strip()
    functional = prompt("Enter the functional to be used (default: wb97xd):").strip() or "wb97xd"
    title = input("Enter title (or press ENTER for default): ").strip() or f"{os.path.splitext(os.path.basename(newchk))[0]} Franck–Condon calculation"

    base = os.path.splitext(os.path.basename(newchk))[0]
    outname = input(f"Enter output filename (default: {base}_fc): ").strip() or f"{base}_fc"
    output_path = f"{outname}.com"
    output_chk = f"{outname}.chk"
    charge = input("Enter charge (default -1): ").strip() or "-1"
    multiplicity = input("Enter multiplicity (default 2): ").strip() or "2"
#    vertical_freq_chk = prompt("Enter vertical freq checkpoint file name: ", completer=chk_completer).strip()

    # FC Method
    fc_methods = ["VerticalHessian", "AdiabaticShift", "AdiabaticHessian", "VerticalGradient"]
    fc_method_completer = WordCompleter(fc_methods)
    fc_method = prompt("Select FC method: ", completer=fc_method_completer).strip()
    if fc_method not in fc_methods:
        print("⚠️ Invalid method. Defaulting to 'AdiabaticHessian'")
        fc_method = "AdiabaticHessian"

    # Temperature
    temperature = input("Enter temperature in K (default 5.0): ").strip() or "5.0"

    include_time_independent = input("Include 'TimeIndependent'? (y/n): ").strip().lower() == 'y'
    include_matrix_output = input("Include 'Output=Matrix=JK'? (y/n): ").strip().lower() == 'y'

    with open(output_path, "w") as f:
        f.write(f"%oldchk={oldchk}\n")
        f.write(f"%chk={output_chk}\n")
        f.write(f"#p {functional} ChkBasis FREQ(ReadFC,FC,ReadFCHT) Geom=Checkpoint NOSYMM guess=read\n\n")
        f.write(f"{title}\n\n")
        f.write(f"{charge} {multiplicity}\n\n")
        f.write(f" Method={fc_method}, Spectrum=(Broadening=Stick,Lower=-10000.0,Upper=40000.0) temperature={temperature}\n\n")
        f.write(f"{newchk}\n")
        if include_time_independent:
            f.write("TimeIndependent\n")
        if include_matrix_output:
            f.write("Output=Matrix=JK\n")
        f.write("\n")

    print(f"\n✅ Franck–Condon input file created: {output_path}")

