#!/usr/bin/env python3
# plot_distributions.py
# type: ignore

from pathlib import Path
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


###############################################################################
# IO
###############################################################################

def read_table(path):
	return pd.read_csv(path, sep="\t")


def safe_filename(name):
	return str(name).replace(" ", "_").replace("|", "_").replace("/", "_")


###############################################################################
# Date handling
###############################################################################

def add_date_fields(df, date_column):

	df = df.copy()

	if date_column not in df.columns:
		return df

	df["Date_parsed"] = pd.to_datetime(
		df[date_column].astype(str),
		errors="coerce"
	)

	df["year"] = df["Date_parsed"].dt.year.astype("Int64")
	df["mlst_capsule"] = (
		df["mlst"].astype(str)
		+ "_"
		+ df["Capsule type"].astype(str)
	)

	return df


###############################################################################
# Distribution plots
###############################################################################

def plot_distribution(df_before, df_after, column, outfile):

	outfile = Path(outfile)
	outfile.parent.mkdir(parents=True, exist_ok=True)

	if column not in df_before.columns:

		plt.figure(figsize=(8,4))
		plt.text(0.5,0.5,f"{column} missing",ha="center",va="center")
		plt.axis("off")
		plt.tight_layout()
		plt.savefig(outfile)
		plt.close()
		return

	before = (
		df_before[column]
		.astype(object)
		.where(df_before[column].notna(),"NA")
		.astype(str)
		.value_counts(normalize=True)
		.rename("Before")
	)

	after = (
		df_after[column]
		.astype(object)
		.where(df_after[column].notna(),"NA")
		.astype(str)
		.value_counts(normalize=True)
		.rename("After")
	)

	data = (
		pd.concat([before,after],axis=1)
		.fillna(0)
	)

	data = data.loc[
		data.max(axis=1).sort_values(ascending=False).index
	]

	ax = data.plot(
		kind="bar",
		figsize=(10,4)
	)

	ax.set_xlabel(column)
	ax.set_ylabel("Fraction")

	plt.tight_layout()
	plt.savefig(outfile)
	plt.close()


###############################################################################
# Temporal dotplots
###############################################################################

def plot_time_dotplot(df_before, df_after, category, outfile, max_categories=50):

	outfile = Path(outfile)
	outfile.parent.mkdir(parents=True, exist_ok=True)

	if category not in df_before.columns:
		return

	before = df_before.copy()
	before["dataset"] = "Before"

	after = df_after.copy()
	after["dataset"] = "After"

	df = pd.concat([before,after],ignore_index=True)

	df = df.dropna(subset=["Date_parsed",category])

	if len(df)==0:
		return

	top = (
		df[category]
		.astype(str)
		.value_counts()
		.head(max_categories)
		.index
	)

	df = df[df[category].astype(str).isin(top)]

	order = (
		df.groupby(category)
		.size()
		.sort_values(ascending=False)
		.index
	)

	y = {x:i for i,x in enumerate(order)}

	fig,ax = plt.subplots(
		figsize=(12,max(5,len(order)*0.25))
	)

	sub = df[df["dataset"]=="Before"]

	ax.scatter(
		sub["Date_parsed"],
		[y[x] for x in sub[category]],
		s=4,
		alpha=0.3,
		label="Before"
	)

	sub = df[df["dataset"]=="After"]

	ax.scatter(
		sub["Date_parsed"],
		[y[x] for x in sub[category]],
		s=12,
		alpha=0.8,
		label="After"
	)

	ax.set_yticks(range(len(order)))
	ax.set_yticklabels(order)

	ax.set_xlabel("Collection date")
	ax.set_ylabel(category)

	ax.legend()

	plt.tight_layout()
	plt.savefig(outfile)
	plt.close()



def plot_retained_fraction(df_before, df_after, country_col, outfile):

	outfile = Path(outfile)
	outfile.parent.mkdir(parents=True, exist_ok=True)

	if country_col not in df_before.columns:
		return

	before = df_before[country_col].value_counts()
	after = df_after[country_col].value_counts()

	retained = (
		pd.concat([before.rename("before"), after.rename("after")], axis=1)
		.fillna(0)
	)

	retained["fraction"] = retained["after"] / retained["before"]
	retained = retained.sort_values("fraction", ascending=False)

	ax = retained["fraction"].plot.bar(figsize=(12, 5))

	ax.set_ylabel("Retained fraction")
	ax.set_xlabel(country_col)
	ax.set_ylim(0, 1.05)

	plt.tight_layout()
	plt.savefig(outfile)
	plt.close()



def plot_temporal_density(df_before, df_after, outfile):

	outfile = Path(outfile)
	outfile.parent.mkdir(parents=True, exist_ok=True)

	before = (
		df_before
		.groupby(df_before["Date_parsed"].dt.to_period("W"))
		.size()
	)

	after = (
		df_after
		.groupby(df_after["Date_parsed"].dt.to_period("W"))
		.size()
	)

	data = pd.concat(
		[
			before.rename("Before"),
			after.rename("After")
		],
		axis=1
	).fillna(0)

	data.index = data.index.astype(str)

	ax = data.plot(figsize=(12, 4))

	ax.set_ylabel("Genomes / week")
	ax.set_xlabel("Week")

	plt.tight_layout()
	plt.savefig(outfile)
	plt.close()



def plot_population(df_after, config, outfile):

	pop_cfg = config["sampling"].get("population", {})

	if not pop_cfg.get("enabled", False):
		return

	pop = pd.read_csv(
		pop_cfg["population_file"],
		sep="\t"
	)

	country_col = config["country_column"]

	counts = (
		df_after[country_col]
		.value_counts()
		.rename("genomes")
	)

	pop = pop.rename(columns={"country": country_col})

	data = pop.merge(
		counts,
		on=country_col,
		how="left"
	).fillna(0)

	fig, ax = plt.subplots(figsize=(6, 6))

	ax.scatter(
		data["population"],
		data["genomes"],
		s=20,
		alpha=0.8
	)

	ax.set_xscale("log")
	ax.set_yscale("log")

	ax.set_xlabel("Population")
	ax.set_ylabel("Sampled genomes")

	plt.tight_layout()
	plt.savefig(outfile)
	plt.close()

###############################################################################
# Composition pie plots
###############################################################################

def plot_composition_pie(df1, df2, col, outfile, top_n=5):

	outfile = Path(outfile)
	outfile.parent.mkdir(parents=True, exist_ok=True)

	if col not in df1.columns:
		plt.figure(figsize=(6, 6))
		plt.text(
			0.5,
			0.5,
			f"{col} missing",
			ha="center",
			va="center"
		)
		plt.axis("off")
		plt.savefig(outfile)
		plt.close()
		return


	def summarize(df):

		values = (
			df[col]
			.fillna("NA")
			.astype(str)
			.value_counts()
		)

		top = values.head(top_n)

		other = values.iloc[top_n:].sum()

		if other:
			top.loc["Other"] = other

		return top


	before = summarize(df1)
	after = summarize(df2)

	fig, axes = plt.subplots(
		1,
		2,
		figsize=(10, 5)
	)

	axes[0].pie(
		before.values,
		labels=before.index,
		autopct="%1.1f%%"
	)

	axes[0].set_title("Before")


	axes[1].pie(
		after.values,
		labels=after.index,
		autopct="%1.1f%%"
	)

	axes[1].set_title("After")


	plt.suptitle(col)

	plt.tight_layout()
	plt.savefig(outfile)
	plt.close()

###############################################################################
# Main
###############################################################################


def main():
	config = snakemake.config

	original = add_date_fields(
		read_table(snakemake.input.original),
		config["date_column"]
	)

	sampled = add_date_fields(
		read_table(snakemake.input.sampled),
		config["date_column"]
	)

	outdir = Path(
		snakemake.params.get(
			"outdir",
			Path(snakemake.output[0]).parent
		)
	)

	outdir.mkdir(parents=True,exist_ok=True)

	time_plots = {
		"time_city": config["sampling"]["temporal"].get("city_column"),
		"time_country": config["country_column"],
		"time_mlst": "mlst",
		"time_capsule": "Capsule type",
	}

	composition_plots = {
		"capsule_top": "Capsule type",
		"mlst_top": "mlst",
		"mlst_capsule_top": "mlst_capsule"
	}

	for plot in snakemake.params.plots:

		if plot == "retained_country":

			plot_retained_fraction(
				original,
				sampled,
				config["country_column"],
				outdir / "retained_country.pdf"
			)

		elif plot == "temporal_density":

			plot_temporal_density(
				original,
				sampled,
				outdir / "temporal_density.pdf"
			)

		elif plot == "population":

			plot_population(
				sampled,
				config,
				outdir / "population.pdf"
			)
		elif plot in composition_plots:

			plot_composition_pie(
				original,
				sampled,
				composition_plots[plot],
				outdir / f"{safe_filename(plot)}.pdf"
			)

		elif plot in time_plots:

			column = time_plots[plot]

			if column is None:
				continue

			plot_time_dotplot(
				original,
				sampled,
				column,
				outdir / f"{safe_filename(plot)}.pdf"
			)

		else:

			plot_distribution(
				original,
				sampled,
				plot,
				outdir / f"{safe_filename(plot)}.pdf"
			)

if __name__ == "__main__":
	main()