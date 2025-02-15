import pandas as pd
import os

# Load the extracted CSV file
csv_path = "/Users/carterstambaugh/Developer/Aprio Software/PDF Parser/Data/extracted_data.csv"
df = pd.read_csv(csv_path)

# ✅ Define columns to check for completeness (EXCLUDING `Scan Comments`)
columns_to_check = [col for col in df.columns if col != "Scan Comments"]

# ✅ Remove incomplete rows (any row with NaN in required columns)
cleaned_df = df.dropna(subset=columns_to_check)

# ✅ Save the cleaned CSV
cleaned_csv_path = "/Users/carterstambaugh/Developer/Aprio Software/PDF Parser/Data/extracted_data_cleaned.csv"
cleaned_df.to_csv(cleaned_csv_path, index=False)

# ✅ Print summary after cleaning
print(f"\n✅ Removed {len(df) - len(cleaned_df)} incomplete rows (excluding `Scan Comments`).")
print(f"✅ Cleaned dataset saved to: {cleaned_csv_path}")

# ✅ Rerun analyze.py on the cleaned dataset


print("\n✅ Analysis complete. Check the new summary files.")