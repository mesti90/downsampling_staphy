from pathlib import Path
import sys


WORKFLOW_DIR = Path(workflow.basedir)

configfile: str(WORKFLOW_DIR / "config" / "config.yaml")

OUT = Path(config["output"])
WORK = Path(config["work"])
SCRIPTS = WORKFLOW_DIR / "scripts"

THREADS = config.get("threads", 8)

sys.path.insert(0, str(SCRIPTS.resolve()))
from utils import *

PLOTS = get_enabled_plots(config)

###############################################################################
# Final targets
###############################################################################

DATASETS = config.get("datasets", ["all", "mrsa"])

rule all:
	input:
		expand(OUT / "samples.downsampled.{dataset}.tsv", dataset=DATASETS),
		expand(WORK / "sampling_statistics.{dataset}.tsv", dataset=DATASETS),
		expand(WORK / "evaluation.{dataset}.tsv", dataset=DATASETS),
		#expand( WORK / "plots/{dataset}/{plot}.pdf", dataset=DATASETS, plot=[safe_plot_name(p) for p in PLOTS] )

###############################################################################
# Input validation
###############################################################################

rule validate_input:
	input:
		config["input"]
	output:
		WORK / "samples.validated.tsv"
	log:
		WORK / "logs/validate_input.log"
	script:
		f"{SCRIPTS}/validate_input.py"


###############################################################################
# Metadata annotation
###############################################################################

rule annotate_metadata:
	input:
		WORK / "samples.validated.tsv"
	output:
		WORK / "samples.annotated.all.tsv"
	log:
		WORK / "logs/annotate_metadata.log"
	script:
		f"{SCRIPTS}/annotate_metadata.py"


###############################################################################
# Create MRSA subset
###############################################################################

rule make_mrsa_subset:
	input:
		WORK / "samples.annotated.all.tsv"
	output:
		WORK / "samples.annotated.mrsa.tsv"
	log:
		WORK / "logs/make_mrsa_subset.log"
	script:
		f"{SCRIPTS}/make_mrsa_subset.py"


###############################################################################
# Downsample genomes
###############################################################################

rule subsample:
	input:
		WORK / "samples.annotated.{dataset}.tsv"
	output:
		samples=OUT / "samples.downsampled.{dataset}.tsv",
		stats=WORK / "sampling_statistics.{dataset}.tsv"
	threads: THREADS
	log:
		WORK / "logs/subsample_{dataset}.log"
	script:
		f"{SCRIPTS}/subsample.py"
###############################################################################
# Evaluate sampling
###############################################################################

rule evaluate_sampling:
	input:
		original=WORK / "samples.annotated.{dataset}.tsv",
		sampled=OUT / "samples.downsampled.{dataset}.tsv"
	output:
		WORK / "evaluation.{dataset}.tsv"
	log:
		WORK / "logs/evaluate_{dataset}.log"
	script:
		f"{SCRIPTS}/evaluate_sampling.py"


###############################################################################
# Plot all genomes
###############################################################################
rule plot_distributions:
	input:
		original=WORK / "samples.annotated.{dataset}.tsv",
		sampled=OUT / "samples.downsampled.{dataset}.tsv"
	output:
		expand( WORK / "plots/{{dataset}}/{plot}.pdf", plot=[safe_plot_name(p) for p in PLOTS] )
	params:
		outdir=lambda wc: WORK / "plots" / wc.dataset,
		plots=PLOTS
	log:
		WORK / "logs/plot_{dataset}.log"
	script:
		f"{SCRIPTS}/plot_distributions.py"