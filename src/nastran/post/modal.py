import pandas as pd
import numpy as np

MODAL_REAL_EIGV_KEYS = {
    'MODE': 'Frequency',
    'EXTRACTIONORDER': 'Inverse Frequency',
    'EIGENVALUE': 'Velocity',
    'RADIANS': 'Damping',
    'CYCLES': 'Damping',
    'GENERALIZEDMASS': 'Frequency',
    'GENERALIZEDSTIFF': 'Real Eigenvalue',
}

def _parse_content(content):
    data = []
    for line in content:
        entries = line.split()
        inner_data = []
        for entry in entries:
            try:
                e = float(entry)
            except ValueError:
                e = np.nan
            finally:
                inner_data.append(e)
        data.append(inner_data)

    return data

def read_modal_f06(filename: str):
    with open(filename, 'r') as file:
        raw_lines = file.readlines()

    for i, line in enumerate(raw_lines):
        if 'R E A L   E I G E N V A L U E S' in line:

            raw_content = []
            j = i+3 # linha após as labels de dados
            while raw_lines[j][0] != '1': # primeiro char na linha final da pagina é 1
                l = raw_lines[j]
                if l.strip() == '':
                    break
                raw_content.append(l)
                j += 1

            parsed_data = _parse_content(raw_content)

            df = pd.DataFrame(parsed_data, columns=list(MODAL_REAL_EIGV_KEYS.keys()))

            return df
