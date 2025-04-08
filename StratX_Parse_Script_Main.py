import re
import os
import pdfplumber
import pandas as pd
from datetime import datetime

# Define lung sections for labeling
lung_sections = ["RUL", "RUL+RML", "RML", "RLL", "LUL", "LLL"]

# Define column headers (excluding 'Site' and 'Folder Name')
columns = [
    "File Name", "Patient ID", "Upload Date", "Scan ID", "Report Date", "CT Scan Date", "Scan Comments", "Scan Status",
    "Fissure Completeness RUL", "Fissure Completeness RUL+RML", "Fissure Completeness RML",
    "Fissure Completeness RLL", "Fissure Completeness LUL", "Fissure Completeness LLL",
    "Voxel Density -910 HU RUL", "Voxel Density -910 HU RUL+RML", "Voxel Density -910 HU RML",
    "Voxel Density -910 HU RLL", "Voxel Density -910 HU LUL", "Voxel Density -910 HU LLL",
    "Voxel Density -950 HU RUL", "Voxel Density -950 HU RUL+RML", "Voxel Density -950 HU RML",
    "Voxel Density -950 HU RLL", "Voxel Density -950 HU LUL", "Voxel Density -950 HU LLL",
    "Inspiratory Volume RUL", "Inspiratory Volume RUL+RML", "Inspiratory Volume RML",
    "Inspiraatory Volume RLL", "Inspiratory Volume LUL", "Inspiratory Volume LLL"
]

def extract_header_info(text, file_name):
    header_data = {
        "File Name": file_name,
        "Patient ID": None, "Upload Date": None, "Scan ID": None, "Report Date": None,
        "CT Scan Date": None, "Scan Comments": None, "Scan Status": "✅ No Warnings"
    }

    patterns = {
        "Patient ID": r"Patient ID\s+([A-Z0-9]+)",
        "Upload Date": r"Upload Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "Scan ID": r"Scan ID\s+([.\d]+)",
        "Report Date": r"Report Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "CT Scan Date": r"CT Scan Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "Scan Comments": r"Scan Comments\s+(.+)"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            header_data[key] = match.group(1).strip()

    if "The following patient order has been rejected" in text or "Not usable" in text:
        header_data["Scan Status"] = "⚠️ Not Usable"
    elif "ATTENTION" in text:
        header_data["Scan Status"] = "⚠️ Warning"

    return header_data

def extract_results_section(text):
    results_start = re.search(r"RESULTS", text)
    if not results_start:
        print("⚠️ 'RESULTS' section not found. Marking as Not Usable.")
        return None

    results_text = text[results_start.end():].strip().split("\n")

    extracted_data = {
        "Fissure Completeness": [], "Voxel Density -910 HU": [], "Voxel Density -950 HU": [], "Inspiratory Volume (ml)": []
    }

    last_seen_label = None
    collecting_numbers = False
    current_numbers = []
    i = 0

    while i < len(results_text):
        line = results_text[i].strip()
        if not line:
            i += 1
            continue

        if "% Fissure" in line:
            last_seen_label = "Fissure Completeness"
            collecting_numbers = True
            current_numbers = []
            i += 1
            continue

        if "% Voxel Density" in line:
            if i + 1 < len(results_text):
                next_line = results_text[i + 1].strip()
                numbers = re.findall(r"\d+", next_line)
                if i + 2 < len(results_text):
                    full_label = f"Voxel Density {results_text[i + 2].strip()}"
                    last_seen_label = "Voxel Density -910 HU" if "-910" in full_label else "Voxel Density -950 HU"
                extracted_data[last_seen_label] = numbers[:6]
            i += 3
            continue

        if "Inspiratory" in line:
            last_seen_label = "Inspiratory Volume (ml)"
            collecting_numbers = True
            current_numbers = []
            i += 1
            continue

        if collecting_numbers and re.search(r"\d+", line):
            numbers_found = re.findall(r"\d+", line)
            current_numbers.extend(numbers_found)

        if last_seen_label and current_numbers:
            extracted_data[last_seen_label] = current_numbers[:6]

        i += 1

    for key in extracted_data:
        if len(extracted_data[key]) != 6:
            extracted_data[key] = (extracted_data[key] + [None] * 6)[:6]

    return extracted_data

def process_pdf(pdf_path):
    file_name = os.path.basename(pdf_path)
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    header_info = extract_header_info(text, file_name)
    results_data = extract_results_section(text)

    if results_data is None:
        header_info["Scan Status"] = "⚠️ Not Usable"
        results_data = {k: [None] * 6 for k in results_data or {"Fissure Completeness": []}}

    unique_id = f"{header_info['Patient ID']}_{header_info['Scan ID']}" if header_info["Patient ID"] and header_info["Scan ID"] else None

    row_data = [
        header_info["File Name"], header_info["Patient ID"], header_info["Upload Date"],
        header_info["Scan ID"], header_info["Report Date"], header_info["CT Scan Date"],
        header_info["Scan Comments"], header_info["Scan Status"]
    ]

    for key in ["Fissure Completeness", "Voxel Density -910 HU", "Voxel Density -950 HU", "Inspiratory Volume (ml)"]:
        row_data.extend(results_data.get(key, [None] * 6))

    return unique_id, row_data

def process_main_folder(main_folder, output_folder):
    data_dict = {}

    for root, _, files in os.walk(main_folder):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                print(f"\n📂 Processing PDF: {pdf_path}")

                unique_id, extracted_data = process_pdf(pdf_path)

                if unique_id and unique_id not in data_dict:
                    data_dict[unique_id] = extracted_data
                else:
                    print(f"⚠️ Duplicate entry skipped: {unique_id}")

    df = pd.DataFrame(list(data_dict.values()), columns=columns)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = os.path.join(output_folder, f"StratX_Parsed_Results_{timestamp}.csv")

    os.makedirs(output_folder, exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Extracted data saved to: {output_csv}")
    clean_csv(output_csv)
    print_summary_results(output_csv)

def clean_csv(csv_path):
    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    columns_to_check = [col for col in df.columns if col != "Scan Comments"]
    cleaned_df = df.dropna(subset=columns_to_check)
    cleaned_df.to_csv(csv_path, index=False)
    print(f"✅ Removed {len(df) - len(cleaned_df)} incomplete rows. Cleaned file saved.")

def print_summary_results(csv_path):
    df = pd.read_csv(csv_path)
    total_rows = len(df)
    no_warnings_count = df[df["Scan Status"] == "✅ No Warnings"].shape[0]
    warnings_count = df[df["Scan Status"].str.contains("⚠️ Warning", na=False)].shape[0]
    errors_count = df[df["Scan Status"].str.contains("⚠️ Not Usable", na=False)].shape[0]

    print("\n📊 Summary Report")
    print(f"Total Rows: {total_rows}")
    print(f"✅ No Warnings: {no_warnings_count}")
    print(f"⚠️ Warnings: {warnings_count}")
    print(f"⚠️ Not Usable: {errors_count}")

def main():
    print("🔍 StratX PDF Processor - Flexible Mode")
    main_folder = input("📂 Drag and drop your main folder here: ").strip().strip("'\"")
    main_folder = main_folder.replace("\\", "")

    if not os.path.exists(main_folder):
        print(f"❌ Folder not found: {main_folder}")
        return

    default_output_folder = os.path.join(main_folder, "StratX_Results")
    confirm = input(f"\nResults will be saved to: {default_output_folder}. Proceed? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ Operation cancelled.")
        return

    process_main_folder(main_folder, default_output_folder)

if __name__ == "__main__":
    main()
