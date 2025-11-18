# ============================================================================
# ENHANCED SAVE FUNCTION - THREE EXCEL WORKBOOK OUTPUTS
# 
# This creates three separate Excel files:
# 1. All_Data.xlsx - Single sheet with all results
# 2. By_System.xlsx - Organized by molecule/system (separate sheets)
# 3. By_Functional.xlsx - Organized by functional (separate sheets)
# ============================================================================

import pandas as pd
from typing import Dict, List
from collections import defaultdict


def save_comparison_results_enhanced(all_results: List[Dict], 
                                     parsed_data: List[Dict],
                                     ignore_patterns: Dict[str, str]) -> None:
    """
    Save comparison results to THREE separate Excel files with different organizations.
    
    Creates:
    1. All_Data.xlsx - Single sheet with all results
    2. By_System.xlsx - One sheet per system (molecule)
    3. By_Functional.xlsx - One sheet per functional
    
    Parameters:
    ----------
    all_results : list
        All comparison results
    parsed_data : list
        Original parsed data with full metadata
    ignore_patterns : dict
        Pattern ignore rules to apply when grouping
    """
    if not all_results:
        print("\n⚠️  No results to save")
        return
    
    print("\n" + "="*80)
    print("💾 SAVE RESULTS")
    print("="*80)
    
    save = input("\nSave results to Excel/CSV? [Y/n]: ").strip().lower()
    
    if save == 'n':
        print("  Results not saved")
        return
    
    # Get base filename
    base_name = input("Output filename base (without extension) [energy_comparison]: ").strip()
    base_name = base_name or "energy_comparison"
    
    print("\n📊 Generating Excel workbooks...")
    
    # Create DataFrames
    df_all = pd.DataFrame(all_results)
    
    # ========================================================================
    # WORKBOOK 1: All Data in Single Sheet
    # ========================================================================
    excel_all = f"{base_name}_All_Data.xlsx"
    try:
        with pd.ExcelWriter(excel_all, engine="xlsxwriter") as writer:
            df_all.to_excel(writer, sheet_name="All_Data", index=False)
            _format_worksheet(writer, "All_Data")
        print(f"✅ Saved: {excel_all}")
    except Exception as e:
        print(f"⚠️  Error saving {excel_all}: {e}")
    
    # ========================================================================
    # WORKBOOK 2: Organized by System (Molecule)
    # ========================================================================
    excel_system = f"{base_name}_By_System.xlsx"
    try:
        system_groups = _organize_by_system(all_results, parsed_data)
        
        with pd.ExcelWriter(excel_system, engine="xlsxwriter") as writer:
            # Create a summary sheet first
            _create_system_summary_sheet(writer, system_groups)
            
            # Create individual sheets for each system
            for system_name, system_data in system_groups.items():
                df_system = pd.DataFrame(system_data)
                # Recalculate ΔE relative to lowest in this system
                df_system = _recalculate_delta_e(df_system)
                
                sheet_name = _sanitize_sheet_name(system_name)
                df_system.to_excel(writer, sheet_name=sheet_name, index=False)
                _format_worksheet(writer, sheet_name, include_system_col=False)
        
        print(f"✅ Saved: {excel_system} ({len(system_groups)} systems)")
    except Exception as e:
        print(f"⚠️  Error saving {excel_system}: {e}")
    
    # ========================================================================
    # WORKBOOK 3: Organized by Functional
    # ========================================================================
    excel_functional = f"{base_name}_By_Functional.xlsx"
    try:
        functional_groups = _organize_by_functional(all_results, parsed_data)
        
        with pd.ExcelWriter(excel_functional, engine="xlsxwriter") as writer:
            # Create a summary sheet first
            _create_functional_summary_sheet(writer, functional_groups)
            
            # Create individual sheets for each functional
            for functional_name, functional_data in functional_groups.items():
                df_functional = pd.DataFrame(functional_data)
                # Recalculate ΔE relative to lowest in this functional
                df_functional = _recalculate_delta_e(df_functional)
                
                sheet_name = _sanitize_sheet_name(functional_name)
                df_functional.to_excel(writer, sheet_name=sheet_name, index=False)
                _format_worksheet(writer, sheet_name, include_functional_col=False)
        
        print(f"✅ Saved: {excel_functional} ({len(functional_groups)} functionals)")
    except Exception as e:
        print(f"⚠️  Error saving {excel_functional}: {e}")
    
    # ========================================================================
    # Also save CSV for compatibility
    # ========================================================================
    csv_file = f"{base_name}_All_Data.csv"
    df_all.to_csv(csv_file, index=False)
    print(f"✅ Saved: {csv_file}")
    
    print("\n" + "="*80)
    print("📁 Output Files Generated:")
    print(f"   1. {excel_all} - All data in one sheet")
    print(f"   2. {excel_system} - Organized by system")
    print(f"   3. {excel_functional} - Organized by functional")
    print(f"   4. {csv_file} - CSV for data processing")
    print("="*80)


def _organize_by_system(all_results: List[Dict], parsed_data: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Organize results by system (molecule), grouping across functionals and basis sets.
    
    Parameters:
    ----------
    all_results : list
        All comparison results
    parsed_data : list
        Original parsed data with molecule information
    
    Returns:
    -------
    dict: System name -> list of results for that system
    """
    # Create a mapping from filename to molecule
    filename_to_molecule = {}
    for record in parsed_data:
        filename_to_molecule[record['filename']] = record.get('molecule', 'Unknown')
    
    # Group results by system
    system_groups = defaultdict(list)
    
    for result in all_results:
        filename = result['Filename']
        system = filename_to_molecule.get(filename, 'Unknown')
        
        # Add system and functional/basis info to result
        enhanced_result = result.copy()
        
        # Extract functional and basis from parsed_data
        for record in parsed_data:
            if record['filename'] == filename:
                enhanced_result['System'] = system
                enhanced_result['Functional'] = record.get('functional', '')
                enhanced_result['Basis'] = record.get('basis', '')
                break
        
        system_groups[system].append(enhanced_result)
    
    return dict(system_groups)


def _organize_by_functional(all_results: List[Dict], parsed_data: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Organize results by functional, grouping across systems and basis sets.
    
    Parameters:
    ----------
    all_results : list
        All comparison results
    parsed_data : list
        Original parsed data with functional information
    
    Returns:
    -------
    dict: Functional name -> list of results for that functional
    """
    # Create a mapping from filename to functional and system
    filename_to_info = {}
    for record in parsed_data:
        filename_to_info[record['filename']] = {
            'functional': record.get('functional', 'Unknown'),
            'molecule': record.get('molecule', 'Unknown'),
            'basis': record.get('basis', 'Unknown')
        }
    
    # Group results by functional
    functional_groups = defaultdict(list)
    
    for result in all_results:
        filename = result['Filename']
        info = filename_to_info.get(filename, {})
        functional = info.get('functional', 'Unknown')
        
        # Add system and basis info to result
        enhanced_result = result.copy()
        enhanced_result['System'] = info.get('molecule', 'Unknown')
        enhanced_result['Functional'] = functional
        enhanced_result['Basis'] = info.get('basis', 'Unknown')
        
        functional_groups[functional].append(enhanced_result)
    
    return dict(functional_groups)


def _recalculate_delta_e(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recalculate ΔE values relative to the lowest energy in the DataFrame.
    
    Parameters:
    ----------
    df : DataFrame
        DataFrame with Energy (Hartree) column
    
    Returns:
    -------
    DataFrame: Updated DataFrame with recalculated ΔE values
    """
    from .utils import hartree_to_ev
    
    if 'Energy (Hartree)' not in df.columns:
        return df
    
    # Find minimum energy
    min_energy = df['Energy (Hartree)'].min()
    
    # Recalculate ΔE
    df['ΔE (Hartree)'] = df['Energy (Hartree)'] - min_energy
    df['ΔE (eV)'] = df['ΔE (Hartree)'].apply(hartree_to_ev)
    
    return df


def _sanitize_sheet_name(name: str) -> str:
    """
    Sanitize sheet name to comply with Excel's requirements.
    
    Excel sheet names must:
    - Be 31 characters or less
    - Not contain: \ / ? * [ ] :
    
    Parameters:
    ----------
    name : str
        Original sheet name
    
    Returns:
    -------
    str: Sanitized sheet name
    """
    # Replace invalid characters
    invalid_chars = ['\\', '/', '?', '*', '[', ']', ':']
    for char in invalid_chars:
        name = name.replace(char, '_')
    
    # Truncate if too long
    if len(name) > 31:
        name = name[:28] + "..."
    
    return name


def _create_system_summary_sheet(writer, system_groups: Dict[str, List[Dict]]):
    """
    Create a summary sheet for system-organized workbook.
    
    Parameters:
    ----------
    writer : ExcelWriter
        The Excel writer object
    system_groups : dict
        Dictionary of system groups
    """
    summary_data = []
    
    for system_name, system_data in system_groups.items():
        df = pd.DataFrame(system_data)
        
        summary_data.append({
            'System': system_name,
            'Number of Files': len(system_data),
            'Functionals Used': ', '.join(sorted(set(d.get('Functional', '') for d in system_data))),
            'Basis Sets Used': ', '.join(sorted(set(d.get('Basis', '') for d in system_data))),
            'Energy Range (eV)': df['ΔE (eV)'].max() - df['ΔE (eV)'].min() if 'ΔE (eV)' in df.columns else 0,
            'Min Energy (Hartree)': df['Energy (Hartree)'].min() if 'Energy (Hartree)' in df.columns else 0
        })
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name="Summary", index=False)
    _format_worksheet(writer, "Summary", is_summary=True)


def _create_functional_summary_sheet(writer, functional_groups: Dict[str, List[Dict]]):
    """
    Create a summary sheet for functional-organized workbook.
    
    Parameters:
    ----------
    writer : ExcelWriter
        The Excel writer object
    functional_groups : dict
        Dictionary of functional groups
    """
    summary_data = []
    
    for functional_name, functional_data in functional_groups.items():
        df = pd.DataFrame(functional_data)
        
        summary_data.append({
            'Functional': functional_name,
            'Number of Files': len(functional_data),
            'Systems Calculated': ', '.join(sorted(set(d.get('System', '') for d in functional_data))),
            'Basis Sets Used': ', '.join(sorted(set(d.get('Basis', '') for d in functional_data))),
            'Energy Range (eV)': df['ΔE (eV)'].max() - df['ΔE (eV)'].min() if 'ΔE (eV)' in df.columns else 0,
            'Min Energy (Hartree)': df['Energy (Hartree)'].min() if 'Energy (Hartree)' in df.columns else 0
        })
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name="Summary", index=False)
    _format_worksheet(writer, "Summary", is_summary=True)


def _format_worksheet(writer, sheet_name: str, 
                     include_system_col: bool = True,
                     include_functional_col: bool = True,
                     is_summary: bool = False):
    """
    Apply formatting to an Excel worksheet.
    
    Parameters:
    ----------
    writer : ExcelWriter
        The Excel writer object
    sheet_name : str
        Name of the sheet to format
    include_system_col : bool
        Whether to include system column in formatting
    include_functional_col : bool
        Whether to include functional column in formatting
    is_summary : bool
        Whether this is a summary sheet (different formatting)
    """
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    
    # Create formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D3D3D3',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    number_format = workbook.add_format({'num_format': '0.0000'})
    energy_format = workbook.add_format({'num_format': '0.000000'})
    
    # Set header format
    worksheet.set_row(0, None, header_format)
    
    if is_summary:
        # Summary sheet formatting
        worksheet.set_column('A:A', 30)  # System/Functional name
        worksheet.set_column('B:B', 15)  # Number of Files
        worksheet.set_column('C:D', 40)  # Lists of methods/basis
        worksheet.set_column('E:E', 18, number_format)  # Energy Range
        worksheet.set_column('F:F', 20, energy_format)  # Min Energy
    else:
        # Data sheet formatting
        col = 0
        
        # Filename
        worksheet.set_column(col, col, 50)
        col += 1
        
        # System (if included)
        if include_system_col:
            worksheet.set_column(col, col, 20)
            col += 1
        
        # Functional (if included)
        if include_functional_col:
            worksheet.set_column(col, col, 15)
            col += 1
        
        # Basis
        worksheet.set_column(col, col, 15)
        col += 1
        
        # Charge, Mult
        worksheet.set_column(col, col + 1, 8)
        col += 2
        
        # Energy (Hartree)
        worksheet.set_column(col, col, 18, energy_format)
        col += 1
        
        # ΔE (Hartree)
        worksheet.set_column(col, col, 15, energy_format)
        col += 1
        
        # ΔE (eV)
        worksheet.set_column(col, col, 12, number_format)
        col += 1
        
        # ⟨S²⟩
        worksheet.set_column(col, col, 10, number_format)


def perform_comparisons_enhanced(valid_groups: Dict[tuple, List[Dict]], 
                                 group_fields: List[str],
                                 ref_method: str):
    """
    Enhanced version that returns both results and parsed_data for use in save function.
    
    Parameters:
    ----------
    valid_groups : dict
        Groups to compare
    group_fields : list
        Fields used for grouping
    ref_method : str
        Reference selection method
    
    Returns:
    -------
    tuple: (all_results, group_summaries, all_parsed_data)
    """
    from .utils import hartree_to_ev
    
    all_results = []
    group_summaries = {}
    all_parsed_data = []
    
    # If method 2, get target charge/mult once
    if ref_method == "2":
        target_charge = input("  Target charge for all groups: ").strip()
        target_mult = input("  Target multiplicity for all groups: ").strip()
    
    for group_idx, (group_key, files) in enumerate(valid_groups.items(), 1):
        # Create readable group name
        group_name = "_".join(str(v) for v in group_key)
        
        print(f"\n{'='*60}")
        print(f"📂 Group {group_idx}/{len(valid_groups)}: {group_name}")
        print(f"   {len(files)} files in this group")
        
        # Sort files by energy for consistent ordering
        files.sort(key=lambda x: x['energy'])
        
        # Store all parsed data
        all_parsed_data.extend(files)
        
        # Determine reference based on selected method
        reference = select_reference_file(files, ref_method, group_name,
                                        locals().get('target_charge'),
                                        locals().get('target_mult'))
        
        if not reference:
            print("   ⚠️  Could not determine reference, using lowest energy")
            reference = files[0]
        
        ref_energy = reference['energy']
        group_data = []
        
        # Display header
        print(f"   Reference: {reference['filename']}")
        print(f"   {'File':<45} {'Chg':>4} {'Mult':>4} {'ΔE (eV)':>10} {'⟨S²⟩':>8}")
        print("   " + "-"*75)
        
        # Calculate relative energies for each file
        for file_data in files:
            # Calculate energy difference
            delta_hartree = file_data['energy'] - ref_energy
            delta_ev = hartree_to_ev(delta_hartree)
            
            # Prepare result record - essential columns only
            result = {
                'Filename': file_data['filename'],
                'Charge': file_data.get('charge', ''),
                'Multiplicity': file_data.get('multiplicity', ''),
                'Energy (Hartree)': file_data['energy'],
                'ΔE (Hartree)': delta_hartree,
                'ΔE (eV)': delta_ev,
                '⟨S²⟩': file_data.get('spin_contam', ''),
            }
            
            group_data.append(result)
            all_results.append(result)
            
            # Display summary line
            fname_short = file_data['filename'][:45]
            charge = str(file_data.get('charge', '?'))
            mult = str(file_data.get('multiplicity', '?'))
            s2_val = file_data.get('spin_contam')
            s2_str = f"{s2_val:.4f}" if s2_val is not None else "N/A"
            
            # Mark reference with a special indicator
            marker = "📍" if file_data == reference else "  "
            print(f"   {marker} {fname_short:<43} {charge:>4} {mult:>4} {delta_ev:>10.4f} {s2_str:>8}")
        
        # Store group summary as DataFrame
        group_summaries[group_name] = pd.DataFrame(group_data)
    
    return all_results, group_summaries, all_parsed_data


def select_reference_file(files: List[Dict], ref_method: str, 
                          group_name: str, target_charge=None,
                          target_mult=None):
    """
    Select the reference file based on the chosen method.
    """
    if ref_method == "1":
        return files[0]
    elif ref_method == "2":
        if target_charge and target_mult:
            for f in files:
                if (str(f.get('charge', '')) == target_charge and 
                    str(f.get('multiplicity', '')) == target_mult):
                    return f
        return files[0]
    elif ref_method == "3":
        return files[0]
    elif ref_method == "4":
        for f in files:
            if f.get('charge') == 0 and f.get('multiplicity') == 1:
                return f
        return files[0]
    return files[0]





