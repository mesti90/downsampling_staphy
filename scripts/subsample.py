#!/usr/bin/env python3
# type: ignore

from pathlib import Path
import numpy as np
import pandas as pd


###############################################################################
# IO
###############################################################################

def read_table(path):
	return pd.read_csv(path, sep="\t")


def write_table(df, path):
	Path(path).parent.mkdir(parents=True, exist_ok=True)
	df.to_csv(path, sep="\t", index=False)


###############################################################################
# Date handling
###############################################################################

def add_pseudo_dates(df, cfg):
	col = cfg["date_column"]
	rng = np.random.default_rng(cfg.get("seed", 42))

	dates = []

	for x in df[col].astype(str):
		if len(x) == 4 and x.isdigit():
			start = pd.Timestamp(f"{x}-01-01")
			dates.append(start + pd.Timedelta(days=int(rng.integers(365))))
		elif len(x) == 7 and x[4] == "-":
			start = pd.Timestamp(f"{x}-01-01")
			dates.append(start + pd.Timedelta(days=int(rng.integers(start.days_in_month))))
		else:
			dates.append(pd.to_datetime(x, errors="coerce"))

	df["sample_date"] = dates
	return df


def add_time_group(df, resolution):
	if resolution == "week":
		df["time_group"] = df["sample_date"].dt.to_period("W").astype(str)
	elif resolution == "month":
		df["time_group"] = df["sample_date"].dt.to_period("M").astype(str)
	elif resolution == "year":
		df["time_group"] = df["sample_date"].dt.to_period("Y").astype(str)
	else:
		raise ValueError(f"Unknown resolution: {resolution}")

	return df


def preprocess(df, cfg):
	country = cfg["country_column"]

	df = df[df[country].notna() & (df[country].astype(str).str.strip() != "")].copy()

	df = add_pseudo_dates(df, cfg)
	df = add_time_group(df, cfg["temporal"]["resolution"])

	return df


###############################################################################
# Sampling
###############################################################################

###############################################################################
# Temporal filtering
###############################################################################

def apply_temporal_filter(df, cfg):

	temporal = cfg["temporal"]

	city_col = temporal["city_column"]
	country_col = cfg["country_column"]

	selected = []

	df = df.copy()

	df["has_city"] = (
		df[city_col]
		.notna()
		& (df[city_col].astype(str).str.strip() != "")
	)

	###############################################################################
	# Known cities: maximum 1 genome / city / week
	###############################################################################

	city_df = df[df["has_city"]]

	if len(city_df):

		for _, group in city_df.groupby(
			[city_col, "time_group"],
			dropna=False
		):

			n = temporal["max_per_city_week"]

			if len(group) > n:
				group = group.sample(
					n=n,
					random_state=cfg["seed"]
				)

			selected.append(group)


	###############################################################################
	# Unknown cities: maximum 2 genomes / country / week
	###############################################################################

	country_df = df[~df["has_city"]]

	if len(country_df):

		for _, group in country_df.groupby(
			[country_col, "time_group"],
			dropna=False
		):

			n = temporal["max_per_country_week_unknown_city"]

			if len(group) > n:
				group = group.sample(
					n=n,
					random_state=cfg["seed"]
				)

			selected.append(group)


	if not selected:
		return df.iloc[0:0]

	return pd.concat(selected).drop(columns=["has_city"])


###############################################################################
# Population filtering
###############################################################################

def apply_population_filter(df, cfg):

	population = cfg["population"]

	if not population.get("enabled", False):
		return df

	pop_file = population["population_file"]
	people_per_genome = population.get("people_per_genome", 1000000)
	minimum = population.get("minimum_per_country", 1)

	country_col = cfg["country_column"]

	pop = pd.read_csv(pop_file, sep="\t")

	if country_col not in pop.columns:
		raise ValueError(
			f"Population file needs column '{country_col}'"
		)

	pop["genome_limit"] = (
		pop["population"] / people_per_genome
	).astype(int)

	pop["genome_limit"] = pop["genome_limit"].clip(lower=minimum)

	limits = dict(
		zip(
			pop[country_col],
			pop["genome_limit"]
		)
	)

	selected = []

	for country, group in df.groupby(country_col, dropna=False):

		limit = limits.get(country)

		if limit is None:
			selected.append(group)
			continue

		if len(group) > limit:
			group = group.sample(
				n=limit,
				random_state=cfg["seed"]
			)

		selected.append(group)

	return pd.concat(selected)

def make_statistics(input_df, temporal_df, final_df, cfg):

	country_col = cfg["country_column"]
	city_col = cfg["temporal"].get("city_column")

	def count_cities(df):
		if not city_col or city_col not in df.columns:
			return np.nan

		return (
			df[city_col]
			.dropna()
			.astype(str)
			.str.strip()
			.replace("", np.nan)
			.dropna()
			.nunique()
		)

	def first_year(df):
		if len(df) == 0:
			return np.nan
		return int(df["sample_date"].dt.year.min())

	def last_year(df):
		if len(df) == 0:
			return np.nan
		return int(df["sample_date"].dt.year.max())

	def first_date(df):
		if len(df) == 0:
			return np.nan
		return df["sample_date"].min().date()

	def last_date(df):
		if len(df) == 0:
			return np.nan
		return df["sample_date"].max().date()

	date_col = cfg["date_column"]

	date_strings = input_df[date_col].astype(str)

	rows = [
		["Genomes", len(input_df), len(temporal_df), len(final_df)],
		["Countries", input_df[country_col].nunique(dropna=True), temporal_df[country_col].nunique(dropna=True), final_df[country_col].nunique(dropna=True)],
		["Cities", count_cities(input_df), count_cities(temporal_df), count_cities(final_df)],
		["First year", first_year(input_df), first_year(temporal_df), first_year(final_df)],
		["Last year", last_year(input_df), last_year(temporal_df), last_year(final_df)],
		["First date", first_date(input_df), first_date(temporal_df), first_date(final_df)],
		["Last date", last_date(input_df), last_date(temporal_df), last_date(final_df)],
		["Retained (%)", 100.0, round(100 * len(temporal_df) / len(input_df), 2), round(100 * len(final_df) / len(input_df), 2)],
		["Missing country", input_df[country_col].isna().sum(), np.nan, np.nan],
		["Missing city", input_df[city_col].isna().sum() if city_col and city_col in input_df.columns else np.nan, np.nan, np.nan],
		["Year-only dates", (date_strings.str.fullmatch(r"\d{4}")).sum(), np.nan, np.nan],
		["Month-only dates", (date_strings.str.fullmatch(r"\d{4}-\d{2}")).sum(), np.nan, np.nan],
		["Full dates", (date_strings.str.fullmatch(r"\d{4}-\d{2}-\d{2}")).sum(), np.nan, np.nan],
	]

	return pd.DataFrame( rows, columns=["Metric", "Input", "Temporal filter", "Final"] )


###############################################################################
# Main
###############################################################################

###############################################################################
# Main
###############################################################################

def main():
	config = snakemake.config
	seed = config.get("seed", 42)

	np.random.seed(seed)

	cfg = {
		"country_column": config["country_column"],
		"date_column": config["date_column"],
		"seed": seed,
		**config["sampling"]
	}

	input_df = preprocess(
		read_table(snakemake.input[0]),
		cfg
	)

	temporal_df = apply_temporal_filter(
		input_df,
		cfg
	)

	final_df = apply_population_filter(
		temporal_df,
		cfg
	)

	write_table(
		final_df,
		snakemake.output.samples
	)

	stats = make_statistics(
		input_df,
		temporal_df,
		final_df,
		cfg
	)

	write_table(
		stats,
		snakemake.output.stats
	)

if __name__ == "__main__":
	main()