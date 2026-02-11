import pandas as pd
import numpy as np
import os
import pdfplumber
import re

# --- HELPER: FIND VALUE IN EXCEL SHEET ---
def get_excel_val(df, search_term, col_idx, row_offset=0):
    """Finds a specific number in an Excel sheet DataFrame.
    Returns (value, None) on success or (None, error_message) on failure.
    """
    try:
        if df.shape[1] <= col_idx:
            return None, f"DataFrame only has {df.shape[1]} columns, but col_idx={col_idx} requested"

        mask = df.iloc[:, 0].astype(str).str.contains(search_term, case=False, na=False)
        if not mask.any():
            return None, f"Search term '{search_term}' not found in column 0"

        target_idx = df[mask].index[0] + row_offset
        if target_idx >= len(df):
            return None, f"row_offset={row_offset} pushes index {target_idx} out of range (max {len(df)-1})"

        val = df.iloc[target_idx, col_idx]

        if pd.isna(val):
            return None, f"Value at row {target_idx}, col {col_idx} is NaN"

        clean_val = str(val).replace(',', '').replace('$', '').replace('%', '').strip()
        return float(clean_val), None
    except Exception as e:
        return None, str(e)


def extract_data():
    print("--- Extracting Bentley Data ---")
    data = {"Name": "Bentley University"}

    excel_file = "IPEDS Bentley University.xlsx"

    if not os.path.exists(excel_file):
        print(f"ERROR: File '{excel_file}' not found in {os.getcwd()}")
        print(f"Files in current directory: {os.listdir('.')}")
        data["Graduation Rate"] = 88.0
        return data

    # --- 0. LIST AVAILABLE SHEETS (for debugging) ---
    try:
        xls = pd.ExcelFile(excel_file)
        print(f"Available sheets: {xls.sheet_names}")
    except Exception as e:
        print(f"ERROR: Cannot open Excel file: {e}")
        return data

    # --- 1. READ EXCEL SHEETS ---
    sheet_map = {
        "df_grad": "Retention and Graduation",
        "df_hr": "Human Resources",
        "df_fin": "Finance",
        "df_adm": "Admission and Test scores",
    }

    sheets = {}
    for key, sheet_name in sheet_map.items():
        if sheet_name not in xls.sheet_names:
            print(f"WARNING: Sheet '{sheet_name}' not found. Available: {xls.sheet_names}")
            # Try a fuzzy match
            for actual in xls.sheet_names:
                if sheet_name.lower() in actual.lower():
                    print(f"  -> Using fuzzy match: '{actual}'")
                    sheet_name = actual
                    break
        try:
            sheets[key] = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
            print(f"Loaded sheet '{sheet_name}': {sheets[key].shape[0]} rows x {sheets[key].shape[1]} cols")
        except Exception as e:
            print(f"ERROR loading sheet '{sheet_name}': {e}")
            sheets[key] = None

    df_grad = sheets.get("df_grad")
    df_hr = sheets.get("df_hr")
    df_fin = sheets.get("df_fin")
    df_adm = sheets.get("df_adm")

    # --- 2. EXTRACT VALUES ---

    # A. GRADUATION RATE (Col 2 = 6-year rate)
    if df_grad is not None:
        val, err = get_excel_val(df_grad, "Graduation rate", 2)
        if err:
            print(f"WARNING [Graduation Rate]: {err}")
            data["Graduation Rate"] = 88.0
        else:
            data["Graduation Rate"] = val
    else:
        data["Graduation Rate"] = 88.0

    # B. RETENTION RATE
    if df_grad is not None:
        val, err = get_excel_val(df_grad, "Retention rates", 1)
        if err:
            print(f"WARNING [Retention Rate]: {err}")
            data["Retention Rate"] = 93.0
        else:
            data["Retention Rate"] = val
    else:
        data["Retention Rate"] = 93.0

    # C. PELL GRADUATION RATE
    if df_grad is not None:
        val, err = get_excel_val(df_grad, "Pell grant recipients", 1, row_offset=1)
        if err:
            print(f"WARNING [Pell Graduation Rate]: {err}")
            data["Pell Graduation Rate"] = 82.0
        else:
            data["Pell Graduation Rate"] = val
    else:
        data["Pell Graduation Rate"] = 82.0

    # D. FACULTY SALARIES
    if df_hr is not None:
        val, err = get_excel_val(df_hr, "All instructional staff total", 1)
        if err:
            print(f"WARNING [Faculty Salaries]: {err}")
            data["Faculty Salaries"] = 142000
        else:
            data["Faculty Salaries"] = val
    else:
        data["Faculty Salaries"] = 142000

    # E. FINANCIAL RESOURCES (Sum of specific categories)
    if df_fin is not None:
        try:
            mask = df_fin.iloc[:, 0].astype(str).str.contains("Core expenses per FTE", case=False, na=False)
            start = df_fin[mask].index
            if len(start) > 0:
                idx = start[0]
                subset = df_fin.iloc[idx+1:idx+15]
                total = 0.0
                targets = ["Instruction", "Research", "Student services", "Institutional support"]
                for i, row in subset.iterrows():
                    label = str(row.iloc[0])
                    if any(t.lower() in label.lower() for t in targets):
                        raw = row.iloc[1]
                        if pd.notna(raw):
                            clean = str(raw).replace(',', '').replace('$', '').strip()
                            total += float(clean)
                            print(f"  Financial: {label} = {clean}")
                data["Financial Resources"] = total if total > 0 else 36000
            else:
                print("WARNING [Financial Resources]: 'Core expenses per FTE' not found")
                data["Financial Resources"] = 36000
        except Exception as e:
            print(f"ERROR [Financial Resources]: {e}")
            data["Financial Resources"] = 36000
    else:
        data["Financial Resources"] = 36000

    # F. SAT SCORES
    if df_adm is not None:
        try:
            m_mask = df_adm.iloc[:, 0].astype(str).str.contains("Math", case=False, na=False)
            e_mask = df_adm.iloc[:, 0].astype(str).str.contains("Evidence-Based", case=False, na=False)

            if not m_mask.any():
                print("WARNING [SAT Math]: 'Math' not found in Admissions sheet")
                data["Standardized Tests"] = 1350
            elif not e_mask.any():
                print("WARNING [SAT EBRW]: 'Evidence-Based' not found in Admissions sheet")
                data["Standardized Tests"] = 1350
            else:
                m_row = df_adm[m_mask].iloc[0]
                e_row = df_adm[e_mask].iloc[0]

                # Verify columns exist
                if df_adm.shape[1] < 4:
                    print(f"WARNING [SAT]: Admissions sheet has only {df_adm.shape[1]} columns, need at least 4")
                    data["Standardized Tests"] = 1350
                else:
                    math_25, math_75 = float(m_row.iloc[1]), float(m_row.iloc[3])
                    ebrw_25, ebrw_75 = float(e_row.iloc[1]), float(e_row.iloc[3])
                    math_avg = (math_25 + math_75) / 2
                    ebrw_avg = (ebrw_25 + ebrw_75) / 2
                    data["Standardized Tests"] = math_avg + ebrw_avg
                    print(f"  SAT Math avg: {math_avg}, EBRW avg: {ebrw_avg}")
        except Exception as e:
            print(f"ERROR [Standardized Tests]: {e}")
            data["Standardized Tests"] = 1350
    else:
        data["Standardized Tests"] = 1350

    # --- 3. CDS PDF BACKUP (Student-Faculty Ratio) ---
    cds_file = "Bentley_CDS.pdf"
    data["Student-Faculty Ratio"] = 12
    if os.path.exists(cds_file):
        try:
            with pdfplumber.open(cds_file) as pdf:
                for page in pdf.pages:
                    txt = page.extract_text()
                    if not txt:
                        continue
                    match = re.search(r"(\d{1,2})\s*to\s*1", txt)
                    if match:
                        data["Student-Faculty Ratio"] = int(match.group(1))
                        break
        except Exception as e:
            print(f"WARNING [CDS PDF]: {e}")

    # --- 4. PROXIES & DEFAULTS ---
    data["Graduation Rate Performance"] = data.get("Graduation Rate", 88.0)
    data["Pell Grad Performance"] = data.get("Graduation Rate", 88.0) - data.get("Pell Graduation Rate", 80.0)
    data["Borrower Debt"] = 27000
    data["Peer Assessment"] = 3.4
    data["College Grads Earning > HS"] = 92

    return data


if __name__ == "__main__":
    print()
    results = extract_data()
    print("\n--- RESULTS ---\n")
    for key, value in results.items():
        print(f"  {key:<35}: {value}")
