import pandas as pd

# Load the extracted CSV file
csv_path = "Data/extracted_data_cleaned.csv"
df = pd.read_csv(csv_path)

# ✅ Total number of rows
total_rows = len(df)

# ✅ Rows with no warnings
no_warnings_count = df[df["Scan Status"] == "✅ No Warnings"].shape[0]

# ✅ Rows with warnings
warnings_count = df[df["Scan Status"].str.contains("⚠️ Warning", na=False)].shape[0]

# ✅ Rows with errors
errors_count = df[df["Scan Status"].str.contains("⚠️ Not Usable", na=False)].shape[0]

# ✅ Rows with complete data (EXCLUDING `Scan Comments`)
columns_to_check = [col for col in df.columns if col != "Scan Comments"]
complete_rows_count = df.dropna(subset=columns_to_check).shape[0]

# ✅ Rows with missing data (EXCLUDING `Scan Comments`)
incomplete_rows_count = total_rows - complete_rows_count

# ✅ Count PDFs that have comments in `Scan Comments`
pdfs_with_comments = df[df["Scan Comments"].notnull()].shape[0]

# ✅ Errors per site
errors_per_site = df[df["Scan Status"].str.contains("⚠️ Not Usable", na=False)]["Site"].value_counts()

# ✅ Warnings per site
warnings_per_site = df[df["Scan Status"].str.contains("⚠️ Warning", na=False)]["Site"].value_counts()

# ✅ Completeness percentage per site
completeness_per_site = df.groupby("Site").apply(lambda x: (x.dropna(subset=columns_to_check).shape[0] / len(x)) * 100)

# ✅ Column completeness (EXCLUDING `Scan Comments`)
column_completeness = df[columns_to_check].notnull().mean() * 100

# ✅ Print formatted report
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

# ✅ Save CSV reports
summary_df = pd.DataFrame({
    "Metric": [
        "Total Rows", "Rows with No Warnings", "Rows with Warnings",
        "Rows with Errors", "Complete Rows (No NaNs)", "Incomplete Rows (With NaNs)",
        "Total PDFs with Comments in `Scan Comments`"
    ],
    "Value": [
        total_rows, no_warnings_count, warnings_count,
        errors_count, complete_rows_count, incomplete_rows_count,
        pdfs_with_comments
    ]
})

summary_csv_path = "/Users/carterstambaugh/Developer/Aprio Software/PDF Parser/Data/extracted_data_summary.csv"
summary_df.to_csv(summary_csv_path, index=False)

errors_per_site.to_csv("/Users/carterstambaugh/Developer/Aprio Software/PDF Parser/Data/errors_per_site.csv")
warnings_per_site.to_csv("/Users/carterstambaugh/Developer/Aprio Software/PDF Parser/Data/warnings_per_site.csv")
column_completeness.to_csv("/Users/carterstambaugh/Developer/Aprio Software/PDF Parser/Data/column_completeness.csv")
completeness_per_site.to_csv("/Users/carterstambaugh/Developer/Aprio Software/PDF Parser/Data/completeness_per_site.csv")

print(f"\n✅ Reports Saved:")
print(f"  - {summary_csv_path}")
print(f"  - errors_per_site.csv")
print(f"  - warnings_per_site.csv")
print(f"  - column_completeness.csv")
print(f"  - completeness_per_site.csv")