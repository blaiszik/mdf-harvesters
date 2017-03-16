import requests
from json import dump
import os
import paths

base_url = "http://www.materialscommons.org/api/pub/datasets"
headers = {"content-type":"application/json"}


#Collects available data from  and saves to the given directory
#out_dir: The path to the directory (which will be created) for the data files
#existing_dir:
#       -1: Remove out_dir if it exists
#        0: Error if out_dir exists (Default)
#        1: Overwrite files in out_dir if there are path collisions
#verbose: Print status messages? Default False
def materials_commons_harvest(out_dir, filename="materials_commons_metadata.json", existing_dir=0, verbose=False):
	if verbose:
		print("Begin harvesting")
	if os.path.exists(out_dir):
		if existing_dir == 0:
			exit("Directory '" + out_dir + "' exists")
		elif not os.path.isdir(out_dir):
			exit("Error: '" + out_dir + "' is not a directory")
		elif existing_dir == -1:
			rmtree(out_dir)
			os.mkdir(out_dir)
	else:
		os.mkdir(out_dir)

	#Fetch records
	res = requests.get(base_url, headers=headers, verify=False)

	with open(os.path.join(out_dir, filename), 'w') as outfile:
		dump(res.json(), outfile)

if __name__ == "__main__":
	materials_commons_harvest(out_dir=paths.datasets+"materials_commons_metadata", filename="materials_commons_metadata.json", existing_dir=1, verbose=True)


