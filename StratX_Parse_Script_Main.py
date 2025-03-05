import re
import os
import re
import pdfplumber
import pandas as pd
from datetime import datetime



# Define lung sections for labeling
lung_sections = ["RUL", "RUL+RML", "RML", "RLL", "LUL", "LLL"]

# Define column headers
columns = [
    "Site", "Folder Name", "File Name", "Patient ID", "Upload Date", "Scan ID", "Report Date", "CT Scan Date", "Scan Comments", "Scan Status",
    "Fissure Completeness RUL", "Fissure Completeness RUL+RML", "Fissure Completeness RML",
    "Fissure Completeness RLL", "Fissure Completeness LUL", "Fissure Completeness LLL",
    "Voxel Density -910 HU RUL", "Voxel Density -910 HU RUL+RML", "Voxel Density -910 HU RML",
    "Voxel Density -910 HU RLL", "Voxel Density -910 HU LUL", "Voxel Density -910 HU LLL",
    "Voxel Density -950 HU RUL", "Voxel Density -950 HU RUL+RML", "Voxel Density -950 HU RML",
    "Voxel Density -950 HU RLL", "Voxel Density -950 HU LUL", "Voxel Density -950 HU LLL",
    "Inspiratory Volume RUL", "Inspiratory Volume RUL+RML", "Inspiratory Volume RML",
    "Inspiraatory Volume RLL", "Inspiratory Volume LUL", "Inspiratory Volume LLL"
]


def extract_header_info(text, file_name, folder_name, site_name):
    """Extracts header information from the PDF."""
    header_data = {
        "Site": site_name,
        "Folder Name": folder_name,
        "File Name": file_name,
        "Patient ID": None,
        "Upload Date": None,
        "Scan ID": None,
        "Report Date": None,
        "CT Scan Date": None,
        "Scan Comments": None,
        "Scan Status": "✅ No Warnings"
    }

    patterns = {
        "Patient ID": r"Patient ID\s+([A-Z0-9]+)",
        "Upload Date": r"Upload Date\s+([A-Za-z]+\.\s+\d{1,2},\s+\d{4})",
        "Scan ID": r"Scan ID\s+([.\d]+)",  # ✅ Fix: Keep leading periods
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

    if "ATTENTION" in text:
        header_data["Scan Status"] = "⚠️ Warning"

    return header_data


def extract_results_section(text):
    """Extracts lung function data from the 'RESULTS' section in the PDF."""
    results_start = re.search(r"RESULTS", text)
    if not results_start:
        print("⚠️ 'RESULTS' section not found. Marking as Not Usable.")
        return None

    results_text = text[results_start.end():].strip().split("\n")

    extracted_data = {
        "Fissure Completeness": [],
        "Voxel Density -910 HU": [],
        "Voxel Density -950 HU": [],
        "Inspiratory Volume (ml)": []
    }

    last_seen_label = None
    collecting_numbers = False
    current_numbers = []
    label_seen_before = set()

    i = 0
    while i < len(results_text):
        line = results_text[i].strip()

        if not line:
            i += 1
            continue

        # ✅ Detect "Fissure Completeness"
        if "% Fissure" in line:
            last_seen_label = "Fissure Completeness"
            collecting_numbers = True
            current_numbers = []
            i += 1
            continue

        # ✅ Detect "Voxel Density" (It needs two lines)
        if "% Voxel Density" in line:
            # ✅ Get the numbers from the next line
            if i + 1 < len(results_text):
                next_line = results_text[i + 1].strip()
                numbers = re.findall(r"\d+", next_line)

                # ✅ Get the label extension from two lines ahead
                if i + 2 < len(results_text):
                    full_label = f"Voxel Density {results_text[i + 2].strip()}"
                    if "-910 HU" in full_label:
                        last_seen_label = "Voxel Density -910 HU"
                    elif "-950 HU" in full_label:
                        last_seen_label = "Voxel Density -950 HU"
                    else:
                        last_seen_label = "Voxel Density"  # Fallback

                # ✅ Store values
                extracted_data[last_seen_label] = numbers[:6]

            i += 3  # Move past both the data and the second part of the label
            continue

        # ✅ Detect "Inspiratory Volume (ml)"
        if "Inspiratory" in line:
            last_seen_label = "Inspiratory Volume (ml)"
            collecting_numbers = True
            current_numbers = []
            i += 1
            continue

        # ✅ Collect numbers under the last seen label
        if collecting_numbers and re.search(r"\d+", line):
            numbers_found = re.findall(r"\d+", line)
            current_numbers.extend(numbers_found)

        # ✅ Store the numbers when we see a new category
        if last_seen_label and current_numbers:
            extracted_data[last_seen_label] = current_numbers[:6]

        i += 1

    # ✅ Ensure Each Category Has 6 Values (Padding if Missing)
    for key in extracted_data:
        if len(extracted_data[key]) != 6:
            extracted_data[key] = (extracted_data[key] + [None] * 6)[:6]

    return extracted_data

def process_pdf(pdf_path, site_name, folder_name):
    """Extracts structured data from a single PDF file."""
    file_name = os.path.basename(pdf_path)

    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    header_info = extract_header_info(text, file_name, folder_name, site_name)
    results_data = extract_results_section(text)

    # If no results found, mark as "Not Usable"
    if results_data is None:
        header_info["Scan Status"] = "⚠️ Not Usable"
        results_data = {
            "Fissure Completeness": [None] * 6,
            "Voxel Density -910 HU": [None] * 6,
            "Voxel Density -950 HU": [None] * 6,
            "Inspiratory Volume (ml)": [None] * 6
        }

    # Unique ID (Patient ID + Scan ID)
    unique_id = None
    if header_info["Patient ID"] and header_info["Scan ID"]:
        unique_id = f"{header_info['Patient ID']}_{header_info['Scan ID']}"

    # ✅ Ensure all extracted values match column order
    row_data = [
        header_info["Parent Folder"],
        header_info["Child Folder"],
        header_info["File Name"],
        header_info["Patient ID"],
        header_info["Upload Date"],
        header_info["Scan ID"],
        header_info["Report Date"], 
        header_info["CT Scan Date"], 
        header_info["Scan Comments"], 
        header_info["Scan Status"]
    ]

    # ✅ Fix: Ensure exactly 6 values per section and print extracted values
    for key in ["Fissure Completeness", "Voxel Density -910 HU", "Voxel Density -950 HU", "Inspiratory Volume (ml)"]:
        values = results_data.get(key, [None] * 6)
        print(f"🔍 Extracted {key}: {values}")  # ✅ Debugging Output
        row_data.extend(values)  

    # ✅ Fix: Enforce column length consistency
    if len(row_data) < len(columns):
        row_data.extend([None] * (len(columns) - len(row_data)))  # Fill with None if too short
    elif len(row_data) > len(columns):
        row_data = row_data[:len(columns)]  # Trim if too long

    print(f"✅ Processed: {file_name} | Row Length: {len(row_data)} | Expected: {len(columns)}")  # ✅ Debugging Output

    return unique_id, row_data

def process_main_folder(main_folder, output_folder):
    """Processes PDFs under each site and saves results in a CSV."""
    data_dict = {}

    for site_name in os.listdir(main_folder):  # Level 1: Sites (Temple, Chicago, etc.)
        site_path = os.path.join(main_folder, site_name)
        if not os.path.isdir(site_path):
            continue

        for folder_name in os.listdir(site_path):  # Level 2: Patient Folders
            folder_path = os.path.join(site_path, folder_name)
            if not os.path.isdir(folder_path):
                continue

            for filename in os.listdir(folder_path):  # Level 3: PDFs
                if filename.endswith(".pdf"):
                    pdf_path = os.path.join(folder_path, filename)
                    print(f"\n📂 Processing PDF: {pdf_path}")

                    unique_id, extracted_data = process_pdf(pdf_path, site_name, folder_name)

                    # ✅ Fix: Avoid duplicate Patient ID + Scan ID entries
                    if unique_id and unique_id not in data_dict:
                        print(f"✅ Adding {unique_id} | Row Length: {len(extracted_data)} | Expected: {len(columns)}")
                        data_dict[unique_id] = extracted_data
                    else:
                        print(f"⚠️ Duplicate entry skipped: {unique_id}")

#     # ✅ Fix: Convert to DataFrame and Save
#     df = pd.DataFrame(list(data_dict.values()), columns=columns)
    
#     # ✅ Debugging: Print DataFrame before saving
#     print("\n🔍 Sample of Extracted Data (Check Last Columns):")
#     print(df.tail())  # Shows last few rows
    
#     df.to_csv(output_csv, index=False)
#     print(f"\n✅ Extracted data saved to {output_csv}") 
    df = pd.DataFrame(list(data_dict.values()), columns=columns)
    print("\n🔍 Sample of Extracted Data (Check Last Columns):")
    print(df.tail())  # Shows last few rows
    
    # Generate timestamped output file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = os.path.join(output_folder, f"StratX_Parsed_Results_{timestamp}.csv")

    
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Save the DataFrame to a CSV file
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Extracted data saved to: {output_csv}")
    
    # ✅ Automatically clean the CSV after saving
    clean_csv(output_csv)
    print_summary_results(output_csv)


def clean_csv(csv_path):
    """Cleans the extracted CSV by removing incomplete rows and overwrites the original file."""
    if not os.path.exists(csv_path):
        print(f"❌ Error: File not found at {csv_path}")
        return

    # Load the dataset
    df = pd.read_csv(csv_path)
    print(f"🔍 Initial dataset loaded. Total rows: {len(df)}")

    # ✅ Define columns to check for completeness (excluding `Scan Comments`)
    columns_to_check = [col for col in df.columns if col != "Scan Comments"]

    # ✅ Remove incomplete rows (any row with NaN in required columns)
    cleaned_df = df.dropna(subset=columns_to_check)

    # ✅ Overwrite the original file with the cleaned dataset
    cleaned_df.to_csv(csv_path, index=False)
    print(f"\n✅ Removed {len(df) - len(cleaned_df)} incomplete rows (excluding `Scan Comments`).")
    print(f"✅ Cleaned dataset saved back to: {csv_path}")

def print_summary_results(csv_path):
    """Generates and prints summary results from the cleaned CSV."""
    df = pd.read_csv(csv_path)
    
    # ✅ Metrics
    total_rows = len(df)
    no_warnings_count = df[df["Scan Status"] == "✅ No Warnings"].shape[0]
    warnings_count = df[df["Scan Status"].str.contains("⚠️ Warning", na=False)].shape[0]
    errors_count = df[df["Scan Status"].str.contains("⚠️ Not Usable", na=False)].shape[0]
    
    columns_to_check = [col for col in df.columns if col != "Scan Comments"]
    complete_rows_count = df.dropna(subset=columns_to_check).shape[0]
    incomplete_rows_count = total_rows - complete_rows_count
    pdfs_with_comments = df[df["Scan Comments"].notnull()].shape[0]
    
    errors_per_site = df[df["Scan Status"].str.contains("⚠️ Not Usable", na=False)]["Site"].value_counts()
    warnings_per_site = df[df["Scan Status"].str.contains("⚠️ Warning", na=False)]["Site"].value_counts()
    completeness_per_site = df.groupby("Site").apply(lambda x: (x.dropna(subset=columns_to_check).shape[0] / len(x)) * 100)
    column_completeness = df[columns_to_check].notnull().mean() * 100
    
    # ✅ Print Summary
    print("\n📊 Summary of Extracted Data")
    print(f"---------------------------------")
    print(f"Total Rows: {total_rows}")
    print(f"Rows with No Warnings (✅ No Warnings): {no_warnings_count}")
    print(f"Rows with Warnings (⚠️ Warning): {warnings_count}")
    print(f"Rows with Errors (⚠️ Not Usable): {errors_count}")
    print(f"Complete Rows (No NaNs, Excluding `Scan Comments`): {complete_rows_count}")
    print(f"Incomplete Rows (With NaNs, Excluding `Scan Comments`): {incomplete_rows_count}")
    print(f"Total PDFs with Comments in `Scan Comments`: {pdfs_with_comments}")
    
    print("\n🔍 Errors Per Site:")
    print(errors_per_site.to_string())
    
    print("\n🔍 Warnings Per Site:")
    print(warnings_per_site.to_string())
    
    print("\n🔍 Column Completeness (Excluding `Scan Comments`):")
    print(column_completeness.to_string())
    
    print("\n🔍 Completeness Per Site (% of Fully Populated Rows):")
    print(completeness_per_site.to_string())


def main():
    print("🔍 Welcome to the StratX PDF Processing Tool!")
    print("📁 This tool extracts structured data from PDFs and generates cleaned CSV reports.")
    print("\n📖 How to use this tool:")
    print("1️⃣ Drag and drop the **main folder** containing all site folders into this window.")
    print("2️⃣ The main folder should have the following structure:")
    print("""
    Example Folder Structure:
        - Data
            - Parent Folder
                - Child Folder
                    - PDF1.pdf
                    - PDF2.pdf
                - Subfolder2
                    - PDF3.pdf
            - Parent Folder
                - Child Folder
                    - PDF4.pdf
    """)
    print("3️⃣ Press Enter after dragging and dropping the folder.")

    main_folder = input("📂 Drag and drop your main folder here: ").strip().strip("'\"")
    main_folder = main_folder.replace("\\", "")  # Remove escape characters


    if not os.path.exists(main_folder):
        print(f"\n❌ Error: The folder '{main_folder}' does not exist. Please check the path and try again.")
        return

    # Default output folder
    default_output_folder = os.path.join(main_folder, "StratX_Results")
    print(f"\n📂 The results CSV will be saved in the following location by default:\n   {default_output_folder}")

    # Ask the user if they want to change the location
    change_location = input("\n❓ Would you like to save the results in a different location? (yes/no): ").strip().lower()
    if change_location == "yes":
        new_output_folder = input("📂 Enter the new folder path where you want to save the results: ").strip().strip("'\"")
        if os.path.exists(new_output_folder):
            default_output_folder = new_output_folder
            print(f"\n✅ New save location set to: {default_output_folder}")
        else:
            print(f"\n❌ Error: The folder '{new_output_folder}' does not exist. Using default location instead.")

    # Ask for confirmation to proceed
    confirm = input("\n✅ Ready to process the PDFs? Type 'yes' to start: ").strip().lower()
    if confirm != "yes":
        print("\n❌ Operation canceled by the user.")
        return

    print(f"\n🚀 Processing PDFs in: {main_folder}")
    process_main_folder(main_folder, default_output_folder)


if __name__ == "__main__":
    main()
    
