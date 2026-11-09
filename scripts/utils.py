def safe_plot_name(name):
	return (
		str(name)
		.replace(" ", "_")
		.replace("|", "_")
		.replace("/", "_")
	)

def get_enabled_plots(config):

	return (
		config["plots"]["distributions"]
		+ [f"time_{x}" for x in config["plots"]["temporal"]]
		+ config["plots"]["qc"]
	)