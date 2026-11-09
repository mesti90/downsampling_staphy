#!/usr/bin/env python3
# type: ignore

import pandas as pd

cfg = snakemake.config["mrsa"]

df = pd.read_csv(snakemake.input[0], sep="\t")

positive = set(cfg["positive_values"])

mask = df[cfg["column"]].fillna("").astype(str).isin(positive)

df[mask].to_csv(snakemake.output[0], sep="\t", index=False)