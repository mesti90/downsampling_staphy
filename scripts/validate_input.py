#!/usr/bin/env python3
# validate_input.py
# type: ignore

from pathlib import Path
import pandas as pd

def read_table(path):
	return pd.read_csv(path, sep="\t")

def write_table(df, path):
	path = Path(path)
	path.parent.mkdir(parents=True, exist_ok=True)
	df.to_csv(path, sep="\t", index=False)


config = snakemake.config
df = read_table(snakemake.input[0])

genome_col = config["genome_column"]

if genome_col not in df.columns:
	raise ValueError(f"Missing genome column: {genome_col}")

df = df[df[genome_col].notna()].copy()
df[genome_col] = df[genome_col].astype(str)
df = df.drop_duplicates(subset=[genome_col])

date_cfg = config.get("date", {})

if date_cfg.get("enabled", False):
	date_col = config["date_column"]

	if date_col not in df.columns:
		raise ValueError(f"Missing date column: {date_col}")

	df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

	if date_cfg.get("resolution") == "year":
		df["year"] = df[date_col].dt.year.astype("Int64")
	elif date_cfg.get("resolution") == "month":
		df["month"] = df[date_col].dt.to_period("M").astype(str)

df = df.replace("", pd.NA)

write_table(df, snakemake.output[0])