# Handles dependency management and build for sprig

# Download URLs - set here if not available as env var

# GBIF SQL format download (DOI)
GBIF_DOWNLOAD_ID = 0010998-260903145123482
GBIF_SPECIMENS_URL = https://api.gbif.org/v1/occurrence/download/request/$(GBIF_DOWNLOAD_ID).zip

# Threat predictions
THREAT_PREDICTIONS_URL = https://zenodo.org/records/10605228/files/Angiosperm_extinction_risk_predictions_v1.csv

# IPNI-CoL ID mapping (from checklistbank mapping tool)
IPNI_COL_MAPPING_URL = https://fixme
# We can submit a checklistbank matching job to generate this mapping file
# - need to work out how to script this part.
# The match job parameters are as follows:
# {
#   "datasetKey": 316691,
#   "ignoreAmbiguousRanks": false,
#   "synonyms": true,
#   "format": "tsv",
#   "sourceDatasetKey": 2006,
#   "mode": "relaxed"
# }
# For now, the results of the matching job are stored in the resources dir
# and the target just copies from there.

# The GBIF dataset ID for the institutional collection being prioritised
GBIF_DATASET_ID_KEW = cd6e21c8-9e8a-493a-8a76-fbf7862069e5
GBIF_DATASET_ID_RB = 4300f8d5-1ae5-49e5-a101-63894b005868
GBIF_DATASET_ID = $(GBIF_DATASET_ID_KEW)

# Environment setup:
# - venv setup
# - installation of packages from requirements.txt 
# - creation of sentinel marker file
VENV_DIR = .venv
VENV_SENTINEL = $(VENV_DIR)/.setup_complete

ifeq ($(OS),Windows_NT)
SYSTEM_PYTHON = python
VENV_BIN = $(VENV_DIR)/Scripts
PYTHON = $(VENV_BIN)/python.exe
PIP = $(VENV_BIN)/pip.exe
else
SYSTEM_PYTHON = python3
VENV_BIN = $(VENV_DIR)/bin
PYTHON = $(VENV_BIN)/python
PIP = $(VENV_BIN)/pip
endif


$(VENV_SENTINEL): 
	@echo "Setting up virtual environment..."
	$(SYSTEM_PYTHON) -m venv $(VENV_DIR)
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt
	touch $@


# Download data files

downloads/$(GBIF_DOWNLOAD_ID).zip:
	@echo "Downloading GBIF specimen summary data..."
	mkdir -p downloads
	curl -sL -o $@ $(GBIF_SPECIMENS_URL)

downloads/col-ipni-match-results.zip:
	@echo "Downloading IPNI-CoL ID mapping data..."
	mkdir -p downloads
	cp resources/col-ipni-match-results.zip downloads/
	# curl -L -o $@ $(IPNI_COL_MAPPING_URL)

downloads/Angiosperm_extinction_risk_predictions_v1.csv:
	@echo "Downloading threat predictions..."
	mkdir -p downloads
	curl -sL -o $@ $(THREAT_PREDICTIONS_URL)

data/threat-predictions.csv: downloads/Angiosperm_extinction_risk_predictions_v1.csv
	mkdir -p data
	@echo "Copying threat predictions..."
	cp $< $@

# Extract data files
data/gbif-specimens.csv: downloads/$(GBIF_DOWNLOAD_ID).zip
	mkdir -p data
	@echo "Extracting GBIF specimens data..."
	unzip -p $< > $@

data/col-ipni-match-results.tsv: downloads/col-ipni-match-results.zip
	mkdir -p data
	@echo "Extracting CoL-IPNI ID mapping data..."
	unzip -p $< > $@

data/threats-prepared.csv: prepare-threats.py data/threat-predictions.csv data/col-ipni-match-results.tsv $(VENV_SENTINEL)
	mkdir -p data
	@echo "Preparing threat predictions data..."
	$(PYTHON) prepare-threats.py data/threat-predictions.csv data/col-ipni-match-results.tsv $@

data/gbif-specimens-prepared.csv: prepare.py data/gbif-specimens.csv data/threats-prepared.csv $(VENV_SENTINEL)
	@echo "Preparing GBIF specimens data (reshaping to wide, adding threat predictions)..."
	$(PYTHON) prepare.py data/gbif-specimens.csv data/threats-prepared.csv $@  --inst_coll_dataset_id $(GBIF_DATASET_ID) --log_level DEBUG

prep: data/gbif-specimens-prepared.csv

data/gbif-specimens-report.md: analyse.py data/gbif-specimens-prepared.csv $(VENV_SENTINEL)
	@echo "Generating GBIF specimens report..."
	$(PYTHON) analyse.py data/gbif-specimens-prepared.csv $@ --dataset_id $(GBIF_DATASET_ID)

md: data/gbif-specimens-report.md

clean:
	rm -rf data 
	
sterilise: clean
	rm -rf downloads