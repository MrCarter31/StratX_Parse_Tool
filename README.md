# StratX_Parse_Tool

🛠 **Features**
- Processes PDF files to extract structured lung function data.
- Cleans incomplete data rows (excluding “Scan Comments”).
- Generates summary reports:
  - Total rows processed
  - Rows with warnings and errors
  - Completeness percentage per site
  - Column completeness percentage
  - Errors and warnings grouped by site
- Automatically saves results as a timestamped CSV file (e.g., `StratX_Parsed_Results_20250101_120000.csv`).

1️⃣ **Prepare your folder structure**  
   - Place all site-specific folders inside a main data folder.
   - Each site folder should contain subfolders with one or more PDF files.  
   Example folder structure:

2️⃣ **Run the tool**  
- Launch the tool from the command line using Python.  
  ```
  python3 StratX_Parse_Script_Main.py
  ```
3️⃣ **Follow the prompts**  
- Drag and drop your main folder (e.g., `StratX_Data`) into the terminal window and press Enter.  
- Confirm or change the output folder location for the CSV file.  
- Type `yes` to start processing.

---

## 📝 What the Tool Does
1. **Processes PDF files** to extract structured lung function data.
2. **Cleans incomplete rows** (excluding "Scan Comments").
3. **Generates summary reports** with detailed statistics:
- Total rows processed
- Rows with warnings and errors
- Completeness percentage per site
- Column completeness percentage
- Errors and warnings grouped by site
4. **Automatically saves results** as a timestamped CSV file (e.g., `StratX_Parsed_Results_20250101_120000.csv`).

---

## 📂 Output Files
The tool generates the following files:
- **Main CSV Report**: Contains the processed data with cleaned rows.


## ⚠️ Prerequisites
- **Python 3.0+**  
- Python libraries: `pandas`, `pdfplumber`, `datetime`, `re`, `os`

To install the required libraries, run:  
```bash
pip install pandas pdfplumber
