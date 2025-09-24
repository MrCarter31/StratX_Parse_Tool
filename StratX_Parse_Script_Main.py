# import re
# import os
# import pdfplumber
# import pandas as pd
# from datetime import datetime

# # Define lung sections for labeling
# lung_sections = ["RUL", "RUL+RML", "RML", "RLL", "LUL", "LLL"]

# # Define column headers (excluding 'Site' and 'Folder Name')
# columns = [
#     "File Name", "Patient ID", "Upload Date", "Scan ID", "Report Date", "CT Scan Date", "Scan Comments", "Scan Status",
#     "Fissure Completeness RUL", "Fissure Completeness RUL+RML", "Fissure Completeness RML",
#     "Fissure Completeness RLL", "Fissure Completeness LUL", "Fissure Completeness LLL",
#     "Voxel Density -910 HU RUL", "Voxel Density -910 HU RUL+RML", "Voxel Density -910 HU RML",
#     "Voxel Density -910 HU RLL", "Voxel Density -910 HU LUL", "Voxel Density -910 HU LLL",
#     "Voxel Density -950 HU RUL", "Voxel Density -950 HU RUL+RML", "Voxel Density -950 HU RML",
#     "Voxel Density -950 HU RLL", "Voxel Density -950 HU LUL", "Voxel Density -950 HU LLL",
#     "Inspiratory Volume RUL", "Inspiratory Volume RUL+RML", "Inspiratory Volume RML",
#     "Inspiraatory Volume RLL", "Inspiratory Volume LUL", "Inspiratory Volume LLL"
# ]

# def extract_header_info(text, file_name):
#     header_data = {
#         "File Name": file_name,
#         "Patient ID": None, "Upload Date": None, "Scan ID": None, "Report Date": None,
#         "CT Scan Date": None, "Scan Comments": None, "Scan Status": "✅ No Warnings"
#     }

#     patterns = {
#         "Patient ID": r"Patient ID\s+([A-Z0-9]+)",
#         "Upload Date": r"Upload Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
#         "Scan ID": r"Scan ID\s+([.\d]+)",
#         "Report Date": r"Report Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
#         "CT Scan Date": r"CT Scan Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
#         "Scan Comments": r"Scan Comments\s+(.+)"
#     }

#     for key, pattern in patterns.items():
#         match = re.search(pattern, text, re.IGNORECASE)
#         if match:
#             header_data[key] = match.group(1).strip()

#     if "The following patient order has been rejected" in text or "Not usable" in text:
#         header_data["Scan Status"] = "⚠️ Not Usable"
#     elif "ATTENTION" in text:
#         header_data["Scan Status"] = "⚠️ Warning"

#     return header_data

# def extract_results_section(text):
#     results_start = re.search(r"RESULTS", text)
#     if not results_start:
#         print("⚠️ 'RESULTS' section not found. Marking as Not Usable.")
#         return None

#     results_text = text[results_start.end():].strip().split("\n")

#     extracted_data = {
#         "Fissure Completeness": [], "Voxel Density -910 HU": [], "Voxel Density -950 HU": [], "Inspiratory Volume (ml)": []
#     }

#     last_seen_label = None
#     collecting_numbers = False
#     current_numbers = []
#     i = 0

#     while i < len(results_text):
#         line = results_text[i].strip()
#         if not line:
#             i += 1
#             continue

#         if "% Fissure" in line:
#             last_seen_label = "Fissure Completeness"
#             collecting_numbers = True
#             current_numbers = []
#             i += 1
#             continue

#         if "% Voxel Density" in line:
#             if i + 1 < len(results_text):
#                 next_line = results_text[i + 1].strip()
#                 numbers = re.findall(r"\d+", next_line)
#                 if i + 2 < len(results_text):
#                     full_label = f"Voxel Density {results_text[i + 2].strip()}"
#                     last_seen_label = "Voxel Density -910 HU" if "-910" in full_label else "Voxel Density -950 HU"
#                 extracted_data[last_seen_label] = numbers[:6]
#             i += 3
#             continue

#         if "Inspiratory" in line:
#             last_seen_label = "Inspiratory Volume (ml)"
#             collecting_numbers = True
#             current_numbers = []
#             i += 1
#             continue

#         if collecting_numbers and re.search(r"\d+", line):
#             numbers_found = re.findall(r"\d+", line)
#             current_numbers.extend(numbers_found)

#         if last_seen_label and current_numbers:
#             extracted_data[last_seen_label] = current_numbers[:6]

#         i += 1

#     for key in extracted_data:
#         if len(extracted_data[key]) != 6:
#             extracted_data[key] = (extracted_data[key] + [None] * 6)[:6]

#     return extracted_data

# def process_pdf(pdf_path):
#     file_name = os.path.basename(pdf_path)

#     try:
#         with pdfplumber.open(pdf_path) as pdf:
#             text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
#     except Exception as e:
#         print(f"❌ Failed to read PDF: {pdf_path} — {e}")
#         return None, None  # Only return early *if* the PDF failed to open

#     header_info = extract_header_info(text, file_name)
#     results_data = extract_results_section(text)

#     if results_data is None:
#         header_info["Scan Status"] = "⚠️ Not Usable"
#         results_data = {
#             "Fissure Completeness": [None] * 6,
#             "Voxel Density -910 HU": [None] * 6,
#             "Voxel Density -950 HU": [None] * 6,
#             "Inspiratory Volume (ml)": [None] * 6
#         }

#     unique_id = f"{header_info['Patient ID']}_{header_info['Scan ID']}" if header_info["Patient ID"] and header_info["Scan ID"] else None

#     row_data = [
#         header_info["File Name"], header_info["Patient ID"], header_info["Upload Date"],
#         header_info["Scan ID"], header_info["Report Date"], header_info["CT Scan Date"],
#         header_info["Scan Comments"], header_info["Scan Status"]
#     ]

#     for key in ["Fissure Completeness", "Voxel Density -910 HU", "Voxel Density -950 HU", "Inspiratory Volume (ml)"]:
#         row_data.extend(results_data.get(key, [None] * 6))

#     return unique_id, row_data



# def process_main_folder(main_folder, output_folder):
#     data_dict = {}

#     for root, _, files in os.walk(main_folder):
#         for file in files:
#             if file.lower().endswith(".pdf"):
#                 pdf_path = os.path.join(root, file)
#                 print(f"\n📂 Processing PDF: {pdf_path}")

#                 unique_id, extracted_data = process_pdf(pdf_path)

#                 if unique_id and unique_id not in data_dict:
#                     data_dict[unique_id] = extracted_data
#                 else:
#                     print(f"⚠️ Duplicate entry skipped: {unique_id}")

#     df = pd.DataFrame(list(data_dict.values()), columns=columns)
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     output_csv = os.path.join(output_folder, f"StratX_Parsed_Results_{timestamp}.csv")

#     os.makedirs(output_folder, exist_ok=True)
#     df.to_csv(output_csv, index=False)
#     print(f"\n✅ Extracted data saved to: {output_csv}")
#     clean_csv(output_csv)
#     print_summary_results(output_csv)

# def clean_csv(csv_path):
#     if not os.path.exists(csv_path):
#         print(f"❌ File not found: {csv_path}")
#         return

#     df = pd.read_csv(csv_path)
#     columns_to_check = [col for col in df.columns if col != "Scan Comments"]
#     cleaned_df = df.dropna(subset=columns_to_check)
#     cleaned_df.to_csv(csv_path, index=False)
#     print(f"✅ Removed {len(df) - len(cleaned_df)} incomplete rows. Cleaned file saved.")

# def print_summary_results(csv_path):
#     df = pd.read_csv(csv_path)
#     total_rows = len(df)
#     no_warnings_count = df[df["Scan Status"] == "✅ No Warnings"].shape[0]
#     warnings_count = df[df["Scan Status"].str.contains("⚠️ Warning", na=False)].shape[0]
#     errors_count = df[df["Scan Status"].str.contains("⚠️ Not Usable", na=False)].shape[0]

#     print("\n📊 Summary Report")
#     print(f"Total Rows: {total_rows}")
#     print(f"✅ No Warnings: {no_warnings_count}")
#     print(f"⚠️ Warnings: {warnings_count}")
#     print(f"⚠️ Not Usable: {errors_count}")

# def main():
#     print("🔍 StratX PDF Processor - Flexible Mode")
#     main_folder = input("📂 Drag and drop your main folder here: ").strip().strip("'\"")
#     main_folder = main_folder.replace("\\", "")

#     if not os.path.exists(main_folder):
#         print(f"❌ Folder not found: {main_folder}")
#         return

#     default_output_folder = os.path.join(main_folder, "StratX_Results")
#     confirm = input(f"\nResults will be saved to: {default_output_folder}. Proceed? (yes/no): ").strip().lower()
#     if confirm != "yes":
#         print("❌ Operation cancelled.")
#         return

#     process_main_folder(main_folder, default_output_folder)

# if __name__ == "__main__":
#     main()
import re
import os
import pdfplumber
import pandas as pd
from datetime import datetime

# Define column headers
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

def extract_header_info(text, file_name):
    header_data = {
        "File Name": file_name, "Patient ID": None, "Upload Date": None, "Scan ID": None,
        "Report Date": None, "CT Scan Date": None, "Scan Comments": "None", "Scan Status": "✅ No Warnings"
    }
    patterns = {
        "Patient ID": r"Patient ID\s+([\w_.-]+)", "Scan ID": r"Scan ID\s+([\d.]+)",
        "Upload Date": r"Upload Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "Report Date": r"Report Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "CT Scan Date": r"(?:CT\s)?Scan Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "Scan Comments": r"Scan Comments\s*([\s\S]*?)(?=SUMMARY|RESULTS|KEY|Fissure Completeness|$)"
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = ' '.join(match.group(1).strip().replace('\n', ' ').split())
            header_data[key] = value if value else "None"
    if "The following patient order has been rejected" in text or "Not usable" in text:
        header_data["Scan Status"] = "⚠️ Not Usable"
    elif "ATTENTION" in text:
        header_data["Scan Status"] = "⚠️ Warning"
    return header_data

def parse_standard_format(text):
    """Robust parser for all standard, non-Thirona reports."""
    results_start = re.search(r"RESULTS", text, re.IGNORECASE)
    if not results_start: return None
    results_text = text[results_start.end():]
    lines = [line.strip() for line in results_text.split('\n') if line.strip()]
    data = {}
    headers_to_find = {
        "Fissure Completeness": "% Fissure", "Voxel Density -910 HU": "-910 HU",
        "Voxel Density -950 HU": "-950 HU", "Inspiratory Volume (ml)": "Inspiratory"
    }
    for key, search_str in headers_to_find.items():
        try:
            header_idx = next(i for i, line in enumerate(lines) if search_str in line)
            for i in range(header_idx, min(header_idx + 3, len(lines))):
                numbers = re.findall(r'\d+', lines[i])
                if len(numbers) >= 6:
                    data[key] = numbers[:6]
                    break
        except StopIteration: continue
    return data if len(data) == 4 else None

def parse_thirona_format(text):
    """Dedicated parser for the specific layout of Thirona reports based on debug output."""
    results_start = re.search(r"RESULTS", text, re.IGNORECASE)
    if not results_start: return None
    results_text = text[results_start.end():]
    lines = [line.strip() for line in results_text.split('\n') if line.strip()]
    data = {}
    try:
        fissure_idx = next(i for i, line in enumerate(lines) if "% Fissure" in line)
        data["Fissure Completeness"] = re.findall(r'\d+', lines[fissure_idx + 1])[:6]

        voxel_headers = [i for i, line in enumerate(lines) if "% Voxel Density" in line]
        data["Voxel Density -910 HU"] = re.findall(r'\d+', lines[voxel_headers[0] + 1])[:6]
        data["Voxel Density -950 HU"] = re.findall(r'\d+', lines[voxel_headers[1] + 1])[:6]

        volume_idx = next(i for i, line in enumerate(lines) if "Inspiratory" in line)
        data["Inspiratory Volume (ml)"] = re.findall(r'\d+', lines[volume_idx + 1])[:6]
    except (StopIteration, IndexError):
        return None
    
    return data if len(data) == 4 and all(len(v) == 6 for v in data.values()) else None

def process_pdf(pdf_path):
    file_name = os.path.basename(pdf_path)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Use the simple default extraction, which our test proved is the best
            full_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            if not full_text: raise ValueError("PDF text could not be extracted.")
    except Exception as e:
        print(f"❌ Failed to read or extract text from PDF: {file_name} — {e}")
        return file_name, [file_name] + [None]*7 + ["⚠️ Failed to Read"] + [None]*24

    header_info = extract_header_info(full_text, file_name)

    # Use the unique combined header to identify the Thirona report
    if "RUL RUL + RML RML RLL LUL LLL" in full_text:
        results_data = parse_thirona_format(full_text)
    else:
        results_data = parse_standard_format(full_text)

    data_keys = ["Fissure Completeness", "Voxel Density -910 HU", "Voxel Density -950 HU", "Inspiratory Volume (ml)"]
    if results_data is None:
        if header_info["Scan Status"] == "✅ No Warnings":
            header_info["Scan Status"] = "⚠️ Parsing Failed"
        results_data = {key: [None] * 6 for key in data_keys}

    unique_id = f"{header_info['Patient ID']}_{header_info['Scan ID']}" if header_info["Patient ID"] and header_info["Scan ID"] else file_name
    row_data = [
        header_info["File Name"], header_info["Patient ID"], header_info["Upload Date"],
        header_info["Scan ID"], header_info["Report Date"], header_info["CT Scan Date"],
        header_info["Scan Comments"], header_info["Scan Status"]
    ]
    for key in data_keys: row_data.extend(results_data.get(key, [None] * 6))
    return unique_id, row_data

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
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
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

def main():
    print("🔍 StratX PDF Processor - Final Version")
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