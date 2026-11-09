#!/usr/bin/env python3
# evaluate_sampling.py
# type: ignore

from pathlib import Path
import pandas as pd


def read_table(path):
	return pd.read_csv(path, sep="\t") if str(path).endswith((".tsv", ".txt")) else pd.read_csv(path)


def compare(df1, df2, col):
	a = df1[col].value_counts(dropna=False).rename("before")
	b = df2[col].value_counts(dropna=False).rename("after")
	out = pd.concat([a, b], axis=1).fillna(0)
	out["fraction"] = out["after"] / out["before"].replace(0, 1)
	out["variable"] = col
	out["group"] = out.index.astype(str)
	return out.reset_index(drop=True)


config = snakemake.config
original = read_table(snakemake.input.original)
sampled = read_table(snakemake.input.sampled)

out = pd.concat(
	[compare(original, sampled, col) for col in config["evaluation"]["compare"] if col in original.columns],
	ignore_index=True
)

Path(snakemake.output[0]).parent.mkdir(parents=True, exist_ok=True)
out.to_csv(snakemake.output[0], sep="\t", index=False)