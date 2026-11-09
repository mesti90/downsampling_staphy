#!/usr/bin/env python3
# type: ignore

from pathlib import Path
import pandas as pd


def read_table(path):
	return pd.read_csv(path, sep="\t") if str(path).endswith((".tsv", ".txt")) else pd.read_csv(path)


def write_table(df, path):
	path = Path(path)
	path.parent.mkdir(parents=True, exist_ok=True)
	df.to_csv(path, sep="\t", index=False)


config = snakemake.config
df = read_table(snakemake.input[0])

for meta in config.get("metadata", []):
	meta_df = read_table(meta["file"])
	left, right = meta.get("left_on", config["genome_column"]), meta.get("right_on", left)
	if left != right:
		meta_df = meta_df.rename(columns={right: left})
	df = df.merge(meta_df, on=left, how="left", suffixes=("", "_metadata"))

df["always_keep"] = False

for rule in config.get("always_keep", []):
	col = rule["column"]
	if col not in df.columns:
		df[col] = False
	df.loc[df[col].isin(rule["values"]), "always_keep"] = True

write_table(df, snakemake.output[0])