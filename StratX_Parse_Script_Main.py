import re
import os
import pdfplumber
import pandas as pd
from datetime import datetime
from typing import Optional

# -----------------------------
# Column headers (unchanged)
# -----------------------------
columns = [
    "File Name", "Patient ID", "Upload Date", "Scan ID", "Report Date", "CT Scan Date", "Scan Comments", "Scan Status",
    "Fissure Completeness RUL", "Fissure Completeness RUL+RML", "Fissure Completeness RML",
    "Fissure Completeness RLL", "Fissure Completeness LUL", "Fissure Completeness LLL",
    "Voxel Density -910 HU RUL", "Voxel Density -910 HU RUL+RML", "Voxel Density -910 HU RML",
    "Voxel Density -910 HU RLL", "Voxel Density -910 HU LUL", "Voxel Density -910 HU LLL",
    "Voxel Density -950 HU RUL", "Voxel Density -950 HU RUL+RML", "Voxel Density -950 HU RML",
    "Voxel Density -950 HU RLL", "Voxel Density -950 HU LUL", "Voxel Density -950 HU LLL",
    "Inspiratory Volume RUL", "Inspiratory Volume RUL+RML", "Inspiratory Volume RML",
    "Inspiratory Volume RLL", "Inspiratory Volume LUL", "Inspiratory Volume LLL"
]

# -----------------------------
# Small normalizer (defensive)
# -----------------------------
def normalize_text(s: str) -> str:
    """
    Normalize some unicode punctuation that occasionally appears in PDFs.
    """
    if not s:
        return s
    return (
        s.replace('\u2013', '-')  # en dash
         .replace('\u2014', '-')  # em dash
         .replace('\u2212', '-')  # unicode minus
    )

# -----------------------------
# Header extraction (unchanged, with tiny normalization)
# -----------------------------
# def extract_header_info(text, file_name):
#     text = normalize_text(text)

#     header_data = {
#         "File Name": file_name, "Patient ID": None, "Upload Date": None, "Scan ID": None,
#         "Report Date": None, "CT Scan Date": None, "Scan Comments": "None", "Scan Status": "✅ No Warnings"
#     }
#     patterns = {
#         "Patient ID": r"Patient ID\s+([\w_.-]+)",
#         "Scan ID": r"Scan ID\s+([\d.]+)",
#         "Upload Date": r"Upload Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
#         "Report Date": r"Report Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
#         "CT Scan Date": r"(?:CT\s)?Scan Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
#         "Scan Comments": r"Scan Comments\s*([\s\S]*?)(?=SUMMARY|RESULTS|KEY|Fissure Completeness|$)"
#     }
#     for key, pattern in patterns.items():
#         match = re.search(pattern, text, re.IGNORECASE)
#         if match:
#             value = ' '.join(match.group(1).strip().replace('\n', ' ').split())
#             header_data[key] = value if value else "None"

#     # Basic status flags
#     lower = text.lower()
#     if "the following patient order has been rejected".lower() in lower or "not usable" in lower:
#         header_data["Scan Status"] = "⚠️ Not Usable"
#     elif "attention" in lower:
#         header_data["Scan Status"] = "⚠️ Warning"
#     return header_data
    text = normalize_text(text)

    header_data = {
        "File Name": file_name, "Patient ID": None, "Upload Date": None, "Scan ID": None,
        "Report Date": None, "CT Scan Date": None, "Scan Comments": "None", "Scan Status": "✅ No Warnings"
    }

    # Primary (labeled) patterns
    patterns = {
        "Patient ID": r"Patient ID\s+([\w_.-]+)",
        "Scan ID": r"Scan ID\s+([\d.]+)",
        "Upload Date": r"Upload Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "Report Date": r"Report Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "CT Scan Date": r"(?:CT\s)?Scan Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "Scan Comments": r"Scan Comments\s*([\s\S]*?)(?=SUMMARY|RESULTS|KEY|Fissure Completeness|$)"
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            value = ' '.join(m.group(1).strip().replace('\n', ' ').split())
            header_data[key] = value if value else "None"

    # --- Fallbacks for minimal LungQ/Thirona layouts (no labels) ---
    # 1) If dates not labeled, grab first three StratX-style dates anywhere
    def find_all_dates(t):
        return re.findall(r"[A-Za-z]+\.\s+\d{1,2},\s+\d{4}", t)

    if not header_data["Upload Date"] or not header_data["CT Scan Date"] or not header_data["Report Date"]:
        dates = find_all_dates(text)
        # Heuristic: first = Upload, second = CT, third = Report (common order in these PDFs)
        if len(dates) >= 3:
            header_data["Upload Date"] = header_data["Upload Date"] or dates[0]
            header_data["CT Scan Date"] = header_data["CT Scan Date"] or dates[1]
            header_data["Report Date"] = header_data["Report Date"] or dates[2]

    # 2) If Scan ID not labeled, try to find a standalone numeric token near the top
    if not header_data["Scan ID"]:
        # Look at the first ~500 chars for something like 5706.1 or a long integer
        head = text[:500]
        m_scan = re.search(r"\b(\d+(?:\.\d+)?)\b", head)
        if m_scan:
            header_data["Scan ID"] = m_scan.group(1)

    # Basic status flags
    lower = text.lower()
    if "the following patient order has been rejected" in lower or "not usable" in lower:
        header_data["Scan Status"] = "⚠️ Not Usable"
    elif "attention" in lower:
        header_data["Scan Status"] = "⚠️ Warning"
    return header_data

def extract_header_info(text, file_name):
    """
    Extract header metadata from StratX/Thirona/LungQ PDFs.
    Robust to:
      - "Patient ID" variants: "Patient ID:", "PatientID", "Patient Identifier"
      - Patient ID on the next line
      - IDs containing . _ - / (+ optional)
      - Unlabeled dates (grabs first three StratX-style dates)
      - Missing labeled Scan ID (grabs first numeric token near top)
    """
    text = normalize_text(text)

    header_data = {
        "File Name": file_name,
        "Patient ID": None,
        "Upload Date": None,
        "Scan ID": None,
        "Report Date": None,
        "CT Scan Date": None,
        "Scan Comments": "None",
        "Scan Status": "✅ No Warnings",
    }

    # -----------------------------
    # Primary (labeled) patterns
    # -----------------------------
    patterns = {
        "Patient ID": r"Patient ID\s+([\w_.-]+)",  # keep the original (fast path)
        "Scan ID": r"Scan ID\s+([\d.]+)",
        "Upload Date": r"Upload Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "Report Date": r"Report Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "CT Scan Date": r"(?:CT\s)?Scan Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "Scan Comments": r"Scan Comments\s*([\s\S]*?)(?=SUMMARY|RESULTS|KEY|Fissure Completeness|$)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            value = " ".join(m.group(1).strip().replace("\n", " ").split())
            header_data[key] = value if value else "None"

    # -----------------------------
    # Patient ID: robust fallbacks
    # -----------------------------
    # 1) Accept common label variants, optional colon, and broader charset (adds '/' and '+')
        # -----------------------------
    # Patient ID: robust fallbacks
    # -----------------------------
    if not header_data["Patient ID"]:
        # 0) Single-line fast path with common variants and optional colon
        m_pid = re.search(
            r"(?:Patient\s*ID|PatientID|Patient\s*Identifier)\s*:?\s*([A-Za-z0-9._/\-+]+)",
            text,
            re.IGNORECASE,
        )
        if m_pid:
            header_data["Patient ID"] = m_pid.group(1)

    if not header_data["Patient ID"]:
        lines = [ln.strip() for ln in text.split("\n")]

        # 1) Find the label line, allowing the label to be broken across lines (e.g., "Patient" / "ID")
        label_idxs = []
        for i, ln in enumerate(lines):
            if re.search(r"^(?:Patient\s*ID|PatientID|Patient\s*Identifier)\b", ln, re.IGNORECASE):
                label_idxs.append(i)
            else:
                # handle "Patient" on one line and "ID" (or "Identifier") at the start of the next
                if re.fullmatch(r"Patient\s*$", ln, re.IGNORECASE) and i + 1 < len(lines):
                    if re.match(r"^(?:ID|Identifier)\b", lines[i + 1], re.IGNORECASE):
                        label_idxs.append(i)

        # 2) From each label index, stitch the next few lines into a candidate string
        def assemble_candidate_value(start_idx: int) -> Optional[str]:
            # Collect up to 3 subsequent non-empty lines
            chunk = []
            for j in range(start_idx + 1, min(start_idx + 5, len(lines))):
                if lines[j]:
                    chunk.append(lines[j])

            if not chunk:
                return None

            # Repair common hyphenated wraps across line breaks: "ABC-" + "\n" + "123" -> "ABC-123"
            stitched = "\n".join(chunk)
            stitched = re.sub(r"-\s*\n\s*", "-", stitched)  # join hyphen-wrapped splits
            stitched = re.sub(r"\s*\n\s*", " ", stitched)   # collapse remaining newlines to spaces

            # Now extract the first token that looks like an ID (allow . _ - / +)
            m_val = re.search(r"([A-Za-z0-9._/\-+]{2,})", stitched)
            return m_val.group(1) if m_val else None

        for idx in label_idxs:
            candidate = assemble_candidate_value(idx)
            if candidate:
                header_data["Patient ID"] = candidate
                break

    # 3) Filename fallback (e.g., StratX_582_635694_0027.pdf -> 582) if still missing
    if not header_data["Patient ID"]:
        name_only = os.path.splitext(file_name)[0]
        tokens = re.split(r"[_\s]+", name_only)
        for tok in tokens:
            if tok.lower() in {"stratx", "lungq", "report"}:
                continue
            if re.fullmatch(r"\d{2,}", tok):  # take first >=2-digit token
                header_data["Patient ID"] = tok
                break

    # Optional last-resort: use the file stem if you prefer a non-empty Patient ID
    # if not header_data["Patient ID"]:
    #     header_data["Patient ID"] = os.path.splitext(file_name)[0]

    # -----------------------------
    # Unlabeled date fallback
    # -----------------------------
    def find_all_dates(t):
        return re.findall(r"[A-Za-z]+\.\s+\d{1,2},\s+\d{4}", t)

    if not header_data["Upload Date"] or not header_data["CT Scan Date"] or not header_data["Report Date"]:
        dates = find_all_dates(text)
        # Heuristic ordering commonly seen: Upload, CT, Report
        if len(dates) >= 3:
            header_data["Upload Date"] = header_data["Upload Date"] or dates[0]
            header_data["CT Scan Date"] = header_data["CT Scan Date"] or dates[1]
            header_data["Report Date"] = header_data["Report Date"] or dates[2]

    # -----------------------------
    # Scan ID fallback (unlabeled)
    # -----------------------------
    if not header_data["Scan ID"]:
        head = text[:500]  # search near top
        m_scan = re.search(r"\b(\d+(?:\.\d+)?)\b", head)  # e.g., 5706.1
        if m_scan:
            header_data["Scan ID"] = m_scan.group(1)

    # -----------------------------
    # Status flags
    # -----------------------------
    lower = text.lower()
    if "the following patient order has been rejected" in lower or "not usable" in lower:
        header_data["Scan Status"] = "⚠️ Not Usable"
    elif "attention" in lower:
        header_data["Scan Status"] = "⚠️ Warning"

    return header_data
# -----------------------------
# Helpers & universal parser
# -----------------------------
def find_numbers_after(lines, idx, min_count=6, lookahead=8):
    """
    From lines[idx+1 : idx+lookahead], return the first line containing at least `min_count` integers.
    Returns a list of strings (6 numbers) or None.
    """
    for i in range(idx + 1, min(idx + 1 + lookahead, len(lines))):
        nums = re.findall(r'\d+', lines[i])
        if len(nums) >= min_count:
            return [n for n in nums[:6]]
    return None

# def parse_results_universal(text):
#     """
#     Version-agnostic RESULTS parser for both StratX (Voiant) and Thirona/LungQ layouts.

#     Strategy:
#       - Start scanning after 'RESULTS'
#       - Find '% Fissure' → numbers
#       - Find *two* '% Voxel Density' sections → numbers
#       - Assign the larger-sum set to -910 and the other to -950
#       - Find 'Inspiratory' → numbers

#     Returns a dict with keys:
#       'Fissure Completeness', 'Voxel Density -910 HU',
#       'Voxel Density -950 HU', 'Inspiratory Volume (ml)'
#     (If some blocks are missing, the dict can be partial.)
#     """
#     text = normalize_text(text)

#     m = re.search(r"RESULTS", text, re.IGNORECASE)
#     if not m:
#         return None

#     # Normalize lines after RESULTS
#     lines = [ln.strip() for ln in text[m.end():].split('\n') if ln.strip()]
#     data = {}

#     # 1) Fissure Completeness
#     try:
#         fiss_idx = next(i for i, ln in enumerate(lines) if re.search(r'%\s*Fissure', ln, re.IGNORECASE))
#         fiss_vals = find_numbers_after(lines, fiss_idx)
#         if fiss_vals:
#             data["Fissure Completeness"] = fiss_vals
#     except StopIteration:
#         pass

#     # 2) Voxel Density (two sections)
#     vox_indices = [i for i, ln in enumerate(lines) if re.search(r'%\s*Voxel\s*Density', ln, re.IGNORECASE)]
#     vox_vals = []
#     for vi in vox_indices[:2]:
#         arr = find_numbers_after(lines, vi)
#         if arr:
#             # store as ints for comparison, return strings later
#             vox_vals.append(list(map(int, arr)))

#     if len(vox_vals) == 2:
#         # The -910 HU set should be ≥ the -950 HU set overall.
#         sum0, sum1 = sum(vox_vals[0]), sum(vox_vals[1])
#         if sum0 >= sum1:
#             vox910, vox950 = vox_vals[0], vox_vals[1]
#         else:
#             vox910, vox950 = vox_vals[1], vox_vals[0]
#         data["Voxel Density -910 HU"] = list(map(str, vox910))
#         data["Voxel Density -950 HU"] = list(map(str, vox950))

#     # 3) Inspiratory Volume
#     try:
#         vol_idx = next(i for i, ln in enumerate(lines) if re.search(r'Inspiratory', ln, re.IGNORECASE))
#         vol_vals = find_numbers_after(lines, vol_idx)
#         if vol_vals:
#             data["Inspiratory Volume (ml)"] = vol_vals
#     except StopIteration:
#         pass

#     return data
def parse_results_universal(text):
    """
    Version-agnostic parser:
      1) Prefer labeled parsing after 'RESULTS' (your original logic),
         with a fix to ensure -910/-950 come from DISTINCT rows.
      2) If 'RESULTS' absent or labeled parse is incomplete, use an unlabeled fallback
         that classifies six-number rows by shape.
    """
    text = normalize_text(text)

    # -----------------------------
    # Labeled path (original)
    # -----------------------------
    m = re.search(r"RESULTS", text, re.IGNORECASE)
    data = {}

    def try_labeled():
        if not m:
            return {}

        lines = [ln.strip() for ln in text[m.end():].split('\n') if ln.strip()]
        out = {}

        # 1) Fissure Completeness (original)
        try:
            fiss_idx = next(i for i, ln in enumerate(lines) if re.search(r'%\s*Fissure', ln, re.IGNORECASE))
            fiss_vals = find_numbers_after(lines, fiss_idx)
            if fiss_vals:
                out["Fissure Completeness"] = fiss_vals
        except StopIteration:
            pass

        # 2) Voxel Density (two sections) — ensure DISTINCT rows
        vox_indices = [i for i, ln in enumerate(lines) if re.search(r'%\s*Voxel\s*Density', ln, re.IGNORECASE)]
        rows = []
        last_row = None
        for vi in vox_indices[:2]:
            arr = find_numbers_after(lines, vi)
            # If we got a row and it equals the previous one, keep scanning forward
            if arr and last_row and arr == last_row:
                # walk forward from vi+1 to find the next distinct integer row
                for j in range(vi + 1, min(vi + 10, len(lines))):
                    toks = re.findall(r"-?\d+(?:\.\d+)?", lines[j])
                    if len(toks) >= 6 and all("." not in t for t in toks[:6]):
                        candidate = [int(t) for t in toks[:6]]
                        if candidate != list(map(int, last_row)):
                            arr = list(map(str, candidate))
                            break
            if arr:
                rows.append(list(map(int, arr)))
                last_row = arr

        if len(rows) == 2:
            # Larger-sum = -910; other = -950
            a, b = rows[0], rows[1]
            if sum(a) >= sum(b):
                vox910, vox950 = a, b
            else:
                vox910, vox950 = b, a
            out["Voxel Density -910 HU"] = [str(v) for v in vox910]
            out["Voxel Density -950 HU"] = [str(v) for v in vox950]

        # 3) Inspiratory Volume (original)
        try:
            vol_idx = next(i for i, ln in enumerate(lines) if re.search(r'Inspiratory', ln, re.IGNORECASE))
            vol_vals = find_numbers_after(lines, vol_idx)
            if vol_vals:
                out["Inspiratory Volume (ml)"] = vol_vals
        except StopIteration:
            pass

        return out

    labeled = try_labeled()
    # If labeled found anything at all, prefer it and return (keeps your prior success rate)
    if labeled:
        return labeled

    # -----------------------------
    # Unlabeled fallback (minimal PDFs)
    # -----------------------------
    lines_all = [ln.strip() for ln in text.split('\n') if ln.strip()]

    # Collect all six-number rows from the whole doc
    six_rows = []
    for ln in lines_all:
        toks = re.findall(r"-?\d+(?:\.\d+)?", ln)
        if len(toks) >= 6:
            six_rows.append(toks[:6])

    # Fissure: first decimal row that looks like percentages
    fiss = None
    for row in six_rows:
        if any("." in t for t in row):
            try:
                vals = [float(x) for x in row]
                if all(0.0 <= v <= 100.0 for v in vals):
                    fiss = row
                    break
            except Exception:
                continue
    if fiss:
        data["Fissure Completeness"] = fiss

    # Voxel density: two DISTINCT integer rows with all values <= 100
    int_rows = []
    seen = set()
    for row in six_rows:
        if all("." not in t for t in row):
            try:
                ints = [int(t) for t in row]
            except ValueError:
                continue
            if all(0 <= v <= 100 for v in ints):
                tpl = tuple(ints)
                if tpl not in seen:
                    seen.add(tpl)
                    int_rows.append(ints)

    if len(int_rows) >= 2:
        int_rows.sort(key=sum, reverse=True)
        data["Voxel Density -910 HU"] = [str(v) for v in int_rows[0]]
        data["Voxel Density -950 HU"] = [str(v) for v in int_rows[1]]

    # Inspiratory Volume: first plausible volume-like row
    vol = None
    for row in six_rows:
        if all("." not in t for t in row):
            try:
                ints = [int(t) for t in row]
            except ValueError:
                continue
            if all(100 <= v <= 20000 for v in ints):  # 3–5 digits typical
                vol = [str(v) for v in ints]
                break
    if vol:
        data["Inspiratory Volume (ml)"] = vol

    return data if data else None
# -----------------------------
# PDF processing
# -----------------------------
def process_pdf(pdf_path):
    file_name = os.path.basename(pdf_path)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            extracted_pages = []
            for p in pdf.pages:
                t = p.extract_text()
                if t:
                    extracted_pages.append(t)
            full_text = "\n".join(extracted_pages)
            if not full_text:
                raise ValueError("PDF text could not be extracted.")
    except Exception as e:
        print(f"❌ Failed to read or extract text from PDF: {file_name} — {e}")
        return file_name, [file_name] + [None]*7 + ["⚠️ Failed to Read"] + [None]*24

    header_info = extract_header_info(full_text, file_name)

    # Use a single universal parser for all layouts
    results_data = parse_results_universal(full_text)

    # Ensure all keys exist; if missing, mark parsing failed (unless already Warning/Not Usable)
    data_keys = ["Fissure Completeness", "Voxel Density -910 HU", "Voxel Density -950 HU", "Inspiratory Volume (ml)"]
    if not results_data or any(k not in results_data for k in data_keys):
        if header_info["Scan Status"] == "✅ No Warnings":
            header_info["Scan Status"] = "⚠️ Parsing Failed"
        if not results_data:
            results_data = {}
        for k in data_keys:
            results_data.setdefault(k, [None] * 6)

    # Unique key for deduplication
    unique_id = f"{header_info['Patient ID']}_{header_info['Scan ID']}" if header_info["Patient ID"] and header_info["Scan ID"] else file_name

    # Compose row
    row_data = [
        header_info["File Name"], header_info["Patient ID"], header_info["Upload Date"],
        header_info["Scan ID"], header_info["Report Date"], header_info["CT Scan Date"],
        header_info["Scan Comments"], header_info["Scan Status"]
    ]
    for key in data_keys:
        row_data.extend(results_data.get(key, [None] * 6))

    return unique_id, row_data

# -----------------------------
# Folder runner + summary
# -----------------------------
def process_main_folder(main_folder, output_folder):
    data_dict = {}

    for root, _, files in os.walk(main_folder):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                print(f"\n📂 Processing PDF: {file}")
                unique_id, extracted_data = process_pdf(pdf_path)
                if unique_id and unique_id not in data_dict:
                    data_dict[unique_id] = extracted_data
                elif unique_id in data_dict:
                    print(f"⚠️ Duplicate entry skipped: {unique_id}")

    df = pd.DataFrame(list(data_dict.values()), columns=columns)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = os.path.join(output_folder, f"StratX_Parsed_Results_{timestamp}.csv")
    os.makedirs(output_folder, exist_ok=True)
    # df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    df.to_csv(output_csv, index=False, encoding='utf-8-sig', sep=';')
    print(f"\n✅ Extracted data saved to: {output_csv}")
    print_summary_results(output_csv)

def print_summary_results(csv_path):
    try:
        df = pd.read_csv(csv_path)
        total_rows = len(df)
        status_counts = df["Scan Status"].value_counts().reindex([
            "✅ No Warnings", "⚠️ Warning", "⚠️ Not Usable",
            "⚠️ Parsing Failed", "⚠️ Failed to Read"
        ], fill_value=0)
        print("\n📊 Summary Report")
        print(f"Total PDFs Processed: {total_rows}")
        print(f"✅ Successfully Parsed: {status_counts['✅ No Warnings']}")
        print(f"⚠️ Warnings (from PDF): {status_counts['⚠️ Warning']}")
        print(f"⚠️ Not Usable (from PDF): {status_counts['⚠️ Not Usable']}")
        print(f"⚠️ Parsing Failed (Script Error): {status_counts['⚠️ Parsing Failed']}")
        print(f"❌ Failed to Read (Corrupt File?): {status_counts['⚠️ Failed to Read']}")
    except FileNotFoundError:
        print(f"❌ Could not find output file to generate summary: {csv_path}")

# -----------------------------
# CLI entrypoint
# -----------------------------
def main():
    print("🔍 StratX PDF Processor - FINAL (Universal Parser)")
    try:
        main_folder_input = input("📂 Drag and drop your main folder here and press Enter: ").strip()
        main_folder = main_folder_input.strip("'\"")
        if not os.path.isdir(main_folder):
            print(f"❌ Folder not found: {main_folder}")
            return
        default_output_folder = os.path.join(main_folder, "StratX_Results")
        confirm = input(f"\nResults will be saved to: {default_output_folder}. Proceed? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("❌ Operation cancelled.")
            return
        process_main_folder(main_folder, default_output_folder)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        input("\nPress Enter to exit.")

if __name__ == "__main__":
    main()