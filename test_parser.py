import re
import os
import pdfplumber

def run_extraction_test(pdf_path):
    """
    This script runs three different text extraction methods on the PDF
    to see which one produces the cleanest, most parsable text.
    """
    print("--- Starting Final PDF Extraction Test ---")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]

            print("\n" + "="*20 + " METHOD 1: Default Extraction " + "="*20)
            text_default = page.extract_text()
            print(text_default)

            print("\n" + "="*20 + " METHOD 2: Layout Extraction " + "="*20)
            text_layout = page.extract_text(layout=True, x_tolerance=2)
            print(text_layout)
            
            print("\n" + "="*20 + " METHOD 3: Table Extraction " + "="*20)
            # This method tries to find structured tables on the page
            tables = page.extract_tables()
            if tables:
                print(f"Found {len(tables)} table(s).")
                for i, table in enumerate(tables):
                    print(f"\n--- Table {i+1} ---")
                    # Print each row of the table
                    for row in table:
                        print([cell.replace('\n', ' ') if cell else '' for cell in row])
            else:
                print("No tables found with this method.")
            
    except Exception as e:
        print(f"\nAn error occurred: {e}")

    print("\n--- Test Complete ---")


if __name__ == "__main__":
    pdf_relative_path = os.path.join("StratX Zips For Jeff-2", "Chicago", "StratX_0027-2", "2501288.pdf")
    print(f"Attempting to open PDF at: {pdf_relative_path}")

    if not os.path.exists(pdf_relative_path):
        print(f"\n!!! FILE NOT FOUND at: {os.path.abspath(pdf_relative_path)} !!!")
    else:
        print("PDF file found. Proceeding with extraction test...")
        run_extraction_test(pdf_relative_path)