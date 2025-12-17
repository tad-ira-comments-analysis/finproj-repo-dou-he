"""
Combine multiple IRS comment CSV files into a single dataset, create a lightly cleaned
text field for transformer models, and export both raw + cleaned outputs.

What this script does:
1) Reads multiple CSV files listed in `CSV_FILES` from `ROOT_DIR`
2) Standardizes the schema by keeping a fixed set of columns (`COLS_KEEP`)
   - missing columns are created as NA
3) Exports a raw combined dataset:
   - comments_all_raw_irs_multi.csv
   - comments_all_raw_irs_multi.jsonl
4) Creates two text fields:
   - text_raw   : original `combinedText`
   - text_clean : lightly cleaned version for transformers (whitespace/noise cleanup)
5) Optionally normalizes tax-code references (if `SECTION_CODES` is non-empty):
   - "section 45Q" / "§ 45Q" -> "45q" (when lowercase=True)
6) Filters out empty/very short cleaned texts (length < 5)
7) Exports the cleaned dataset:
   - tot_comments_all_clean_irs_multi.csv
   - tot_comments_all_clean_irs_multi.json
"""

from __future__ import annotations
import re
from pathlib import Path
import numpy as np
import pandas as pd

# Set the root directory where the data files are stored
ROOT_DIR = Path(".")

# Key columns to keep in the final dataset
COLS_KEEP = [
    "docketId",
    "commentId",
    "title",
    "trackingNbr",
    "organizationName",
    "firstName",
    "lastName",
    "city",
    "stateProvinceRegion",
    "country",
    "combinedText",
]

# CSV files to be merged
CSV_FILES = []

# Code sections of interest (e.g. "45Q", "179D", etc.)
#    Used to normalize references like "section ..." / "§ ..." into a consistent format.
SECTION_CODES = []


# Text preprocess for BERT/transformers (light)
def clean_for_bert(x, lowercase: bool = True):

    if pd.isna(x):
        return np.nan

    s = str(x)
    s = re.sub(r"[\r\n\t]", " ", s)

    s = re.sub(r"(?i)see attached file\(s\)", " ", s)
    s = re.sub(r"(?i)see attached files", " ", s)
    s = s.replace("[PDF_TEXT]", " ")

    s = s.replace("•", " ")
    s = s.replace("’", "'")
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return np.nan

    # --- Section code normalization ---
    if lowercase:
        s = s.lower()
        codes = sorted([c.lower() for c in SECTION_CODES], key=len, reverse=True)

        for code in codes:
            # e.g. section 45q -> 45q
            s = re.sub(rf"section\s*{code}", code, s)
            # e.g. §45q -> 45q
            s = re.sub(rf"§\s*{code}", code, s)
    else:
        codes = sorted(SECTION_CODES, key=len, reverse=True)
        for code in codes:
            s = re.sub(
                rf"[sS]ection\s*{code}",
                code,
                s,
            )
            s = re.sub(rf"§\s*{code}", code, s)
    return s if s else np.nan


# Read a single CSV and standardize its column schema
def read_one_comments_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    for col in COLS_KEEP:
        if col not in df.columns:
            df[col] = pd.NA

    cols = list(COLS_KEEP)
    return df.loc[:, cols].copy()


# Main pipeline: combine >>> clean >>> export
def main():
    # ---------- Read and merge all csv ----------
    dfs = []
    for fname in CSV_FILES:
        fpath = ROOT_DIR / fname
        print(f"[INFO] Reading: {fpath}")
        if not fpath.exists():
            print(f"File not found, skipping: {fpath}")
            continue
        df_i = read_one_comments_csv(fpath)
        dfs.append(df_i)

    if not dfs:
        raise RuntimeError("No CSV files were successfully read.")

    comments_all_raw = pd.concat(dfs, ignore_index=True)

    print("\n Raw combined ")
    print("Shape:", comments_all_raw.shape)
    print(comments_all_raw.head())

    # ---------- Export the combined (raw, uncleaned) dataset ----------
    raw_csv_path = ROOT_DIR / "comments_all_raw_irs_multi.csv"
    raw_jsonl_path = ROOT_DIR / "comments_all_raw_irs_multi.jsonl"

    comments_all_raw.to_csv(raw_csv_path, index=False)
    comments_all_raw.to_json(
        raw_jsonl_path,
        orient="records",
        lines=True,
        force_ascii=False,
    )

    print(f"\n Saved raw combined CSV to: {raw_csv_path}")
    print(f"\n Saved raw combined JSONL to: {raw_jsonl_path}")

    # ---------- Clean text (for transformer models) ----------
    comments_all = comments_all_raw.copy()
    comments_all["text_raw"] = comments_all["combinedText"]

    comments_all["text_clean"] = comments_all["combinedText"].apply(
        lambda x: clean_for_bert(x, lowercase=True)
    )

    mask = comments_all["text_clean"].notna() & comments_all["text_clean"].str.len().ge(5)
    comments_all_clean = comments_all.loc[mask].reset_index(drop=True)

    print("\n Clean combined ")
    print("Shape:", comments_all_clean.shape)
    print(
        comments_all_clean[
            ["docketId", "commentId", "text_clean"]
        ].head()
    )

    # ---------- Export cleaned result ----------
    clean_csv_path = ROOT_DIR / "tot_comments_all_clean_irs_multi.csv"
    clean_jsonl_path = ROOT_DIR / "tot_comments_all_clean_irs_multi.jsonl"

    comments_all_clean.to_csv(clean_csv_path, index=False)
    comments_all_clean.to_json(
        clean_jsonl_path,
        orient="records",
        lines=True,
        force_ascii=False,
    )

    print(f"\n Saved clean combined CSV to: {clean_csv_path}")
    print(f"Saved clean combined JSONL to: {clean_jsonl_path}")


if __name__ == "__main__":
    main()
