import os
import re
from collections import defaultdict

class FilenameParser:
    """
    A flexible parser for extracting metadata from Gaussian log filenames.
    
    Handles various naming conventions by recognizing known functionals, 
    basis sets, and metadata patterns (charge, multiplicity, etc.).
    """
    
    # Common DFT functionals (add more as needed)
    FUNCTIONALS = {
        # General Hybrid and GGA
        'HF', 'BLYP', 'PBEPBE', 'PBE1PBE', 'TPSSh',
        'B3LYP', 'B3P86', 'B3PW91', 'O3LYP',
        # Dispersion-Corrected
        'APFD', 'APF', 'wB97XD',
        # Long-Range-Corrected
        'LC-wHPBE', 'LC-wPBE', 'CAM-B3LYP', 'wB97X', 'wB97',
        # Truhlar Group
        'MN15', 'M11', 'SOGGA11X', 'N12SX', 'MN12SX',
        'PW6B95', 'PW6B95D3', 'M08HX',
        'M06', 'M06HF', 'M062X', 'M05', 'M052X',
        # PBE Correlation-Based Hybrids
        'PBE1PBE', 'HSEH1PBE', 'OHSE2PBE', 'OHSE1PBE', 'PBEh1PBE',
        # One-Parameter Hybrids
        'B1B95', 'B1LYP', 'mPW1PW91', 'mPW1LYP', 'mPW1PBE', 'mPW3PBE',
        # B97 Revisions
        'B98', 'B971', 'B972',
        # τ-dependent hybrids
        'tHCTHhyb', 'BMK',
        # Older/Legacy Hybrids
        'X3LYP', 'HISSbPBE',
        # Half-and-Half Hybrids
        'BHandH', 'BHandHLYP',
        # Exchange-only Functionals
        'PW91', 'mPW', 'G96', 'O', 'TPSS', 'RevTPSS', 'BRx', 'PKZB', 'wPBEh', 'PBEh',
        # Correlation-only Functionals
        'VWN', 'VWN5', 'LYP', 'PL', 'P86', 'PW91', 'B95',
        'TPSS', 'RevTPSS', 'KCIS', 'BRC', 'PKZB',
        # Combined correlation variations
        'VP86', 'V5LYP',
        # Standalone Pure Functionals
        'VSXC', 'HCTH', 'HCTH93', 'HCTH147', 'HCTH407', 'tHCTH',
        'B97D', 'B97D3',
        'M06L', 'SOGGA11', 'M11L', 'MN12L', 'N12', 'MN15L',
    }
    
    # Common basis set patterns
    BASIS_PATTERNS = [
        # Minimal and Split-Valence
        'STO-3G', '3-21G', '6-21G', '4-31G',
        '6-31G', '6-31G(d)', '6-31+G(d,p)', "6-31G(d')", "6-31G(d',p')",
        '6-311G', '6-311+G(d)', '6-311+G(d,p)', '6-311++G(d,p)',
        # Dunning correlation-consistent
        'cc-pVDZ', 'cc-pVTZ', 'cc-pVQZ', 'cc-pV5Z', 'cc-pV6Z',
        'aug-cc-pVDZ', 'aug-cc-pVTZ', 'aug-cc-pVQZ', 'aug-cc-pV5Z', 'aug-cc-pV6Z',
        'daug-cc-pVDZ', 'daug-cc-pVTZ', 'spaug-cc-pVDZ', 'jul-cc-pVDZ',
        'Jun-cc-pVDZ', 'May-cc-pVDZ', 'Apr-cc-pVDZ',
        # Ahlrichs/Weigend def2 sets
        'def2SVP', 'def2SVPP', 'def2TZVP', 'def2TZVPP',
        'def2QZVP', 'def2QZVPP',
        # ECP & pseudopotentials
        'LanL2MB', 'LanL2DZ', 'SDD', 'SDDAll',
        'CEP-4G', 'CEP-31G', 'CEP-121G',
        'SHC', 'SEC',
        # D95 and variations
        'D95', 'D95V',
        # Other built-ins and specialty
        'SV', 'SVP', 'TZV', 'TZVP', 'QZVP',
        'MidiX', 'MTSmall', 'CBSB7',
        'EPR-II', 'EPR-III',
        'DGDZVP', 'DGDZVP2', 'DGTZVP',
        'UGBS', 'UGBS1P', 'UGBS2P', 'UGBS3P',
        'UGBS1V', 'UGBS2V', 'UGBS3V',
        'UGBS1O', 'UGBS2O', 'UGBS3O',
        # Generic/genecp
        'gen', 'genecp',
#        # Pople-style basis sets
#        r'sto-\d+g',
#        r'\d+-\d+g(\*{0,2}|\([d,p,f,g,+\*]+\))',
#        r'\d+-\d+\+{1,2}g(\*{0,2}|\([d,p,f,g,+\*]+\))',
#        
#        # Correlation-consistent basis sets
#        r'(aug-|d-|t-|q-)?(cc|pv)(d|t|q|5|6)z(-pp|-dk|-f12)?',
#        
#        # Dunning basis sets (alternate notation)
#        r'(aug-)?cc-p(v|c)(d|t|q|5|6)z',
#        
#        # Ahlrichs basis sets (def2 family)
#        r'def2-(s|sv|svp|tzvp|tzvpp|tzvppd|qzvp|qzvpp|qzvppd)',
#        r'(ma-)?def2-(s|sv|svp|tzvp|tzvpp|tzvppd|qzvp|qzvpp|qzvppd)',
#        
#        # Karlsruhe basis sets
#        r'def-(s|sv|svp|tzvp|qzvp)',
#        
#        # Polarization-consistent basis sets
#        r'pc-\d+',
#        r'aug-pc-\d+',
#        
#        # Jensen basis sets
#        r'(aug-)?pc(seg)?-\d+',
#        
#        # Other common basis sets
#        r'dgdzvp', r'lanl2(dz|mb|tz)', r'sdd', r'sddall',
#        r'midix', r'epr-iii?', r'ugbs',
#        r'gen', r'genecp',
#        
#        # Custom/mixed basis sets
#        r'mix-[a-z0-9-]+',
    ]
    
    # Charge and multiplicity patterns
    CHARGE_PATTERN = r'[qQ]([+-]?\d+)'
    MULTIPLICITY_PATTERN = r'[mM](\d+)'
    
    def __init__(self):
        """Initialize the parser with compiled regex patterns."""
        self.functional_set = {f.lower() for f in self.FUNCTIONALS}
        self.basis_regex = re.compile(
            '|'.join(f'({pattern})' for pattern in self.BASIS_PATTERNS),
            re.IGNORECASE
        )
        self.charge_regex = re.compile(self.CHARGE_PATTERN)
        self.mult_regex = re.compile(self.MULTIPLICITY_PATTERN)
    
    def parse_filename(self, filename):
        """
        Parse a filename to extract metadata.
        
        Parameters
        ----------
        filename : str
            The log filename (with or without .log extension)
            
        Returns
        -------
        dict
            Dictionary containing:
            - system_name: The molecule/system identifier
            - functional: The DFT functional or method
            - basis_set: The basis set
            - charge: Integer charge (or None)
            - multiplicity: Integer multiplicity (or None)
            - raw_filename: Original filename
            - parsing_confidence: 'high', 'medium', or 'low'
        """
        # Remove .log extension if present
        base = filename[:-4] if filename.endswith('.log') else filename
        
        # Split by underscores
        parts = base.split('_')
        
        result = {
            'system_name': None,
            'functional': None,
            'basis_set': None,
            'charge': None,
            'multiplicity': None,
            'raw_filename': filename,
            'parsing_confidence': 'low',
            'unparsed_parts': []
        }
        
        # Extract charge and multiplicity first (they're usually at the end)
        charge_parts = []
        mult_parts = []
        other_parts = []
        
        for part in parts:
            if self.charge_regex.fullmatch(part):
                match = self.charge_regex.match(part)
                result['charge'] = int(match.group(1))
                charge_parts.append(part)
            elif self.mult_regex.fullmatch(part):
                match = self.mult_regex.match(part)
                result['multiplicity'] = int(match.group(1))
                mult_parts.append(part)
            else:
                other_parts.append(part)
        
        # Find functional and basis set
        functional_idx = None
        basis_idx = None
        
        for i, part in enumerate(other_parts):
            # Check if this part is a known functional
            if part.lower() in self.functional_set and functional_idx is None:
                result['functional'] = part
                functional_idx = i
            # Check if this part matches a basis set pattern
            elif self.basis_regex.fullmatch(part) and basis_idx is None:
                result['basis_set'] = part
                basis_idx = i
        
        # Determine system name
        if functional_idx is not None:
            # Everything before the functional is the system name
            result['system_name'] = '_'.join(other_parts[:functional_idx])
            result['parsing_confidence'] = 'high'
        elif basis_idx is not None:
            # If we found basis but no functional, assume basis is preceded by functional
            if basis_idx > 0:
                result['functional'] = other_parts[basis_idx - 1]
                result['system_name'] = '_'.join(other_parts[:basis_idx - 1])
                result['parsing_confidence'] = 'medium'
            else:
                result['system_name'] = '_'.join(other_parts)
                result['parsing_confidence'] = 'low'
        else:
            # Fallback: use old convention (first part is system, last two are method/basis)
            if len(other_parts) >= 3:
                result['system_name'] = other_parts[0]
                result['functional'] = other_parts[-2]
                result['basis_set'] = other_parts[-1]
                result['parsing_confidence'] = 'low'
            else:
                result['system_name'] = '_'.join(other_parts)
                result['parsing_confidence'] = 'low'
        
        # Track unparsed parts for debugging
        parsed_parts = set()
        if result['system_name']:
            parsed_parts.update(result['system_name'].split('_'))
        if result['functional']:
            parsed_parts.add(result['functional'])
        if result['basis_set']:
            parsed_parts.add(result['basis_set'])
        
        result['unparsed_parts'] = [p for p in other_parts if p not in parsed_parts]
        
        return result
    
    def validate_parse(self, parse_result, verbose=False):
        """
        Validate the parsing result and return warnings if needed.
        
        Parameters
        ----------
        parse_result : dict
            Result from parse_filename()
        verbose : bool
            If True, print validation warnings
            
        Returns
        -------
        list
            List of validation warnings (empty if all good)
        """
        warnings = []
        
        if not parse_result['functional']:
            warnings.append(f"Could not identify functional in '{parse_result['raw_filename']}'")
        
        if not parse_result['basis_set']:
            warnings.append(f"Could not identify basis set in '{parse_result['raw_filename']}'")
        
        if not parse_result['system_name']:
            warnings.append(f"Could not identify system name in '{parse_result['raw_filename']}'")
        
        if parse_result['parsing_confidence'] == 'low':
            warnings.append(f"Low confidence in parsing '{parse_result['raw_filename']}'")
        
        if parse_result['unparsed_parts']:
            warnings.append(f"Unparsed parts in '{parse_result['raw_filename']}': {parse_result['unparsed_parts']}")
        
        if verbose and warnings:
            print(f"\n⚠️  Validation warnings for {parse_result['raw_filename']}:")
            for w in warnings:
                print(f"   - {w}")
        
        return warnings



