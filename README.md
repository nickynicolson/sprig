# sprig
specimen prioritisation rules for institutional georeferencing

## Rationale

This repository defines a SQL format download from GBIF and processes it for use in the prioritisation of specimens for georeferencing within an institutional collection. 

It is intended for use by the institutional holder of a particular specimen collection, which is mobilised to GBIF in a single dataset. The dataset ID must be supplied to the analysis process.

## Prioritisation criteria

1. Specimen represents a species that is assessed as threatened according to [Bachman 2024](https://doi.org/10.1111/nph.19592)
2. Specimens of species where the GBIF occurrence holdings are entirely (or majority) drawn from the institutional collection.
3. Specimens of species with fewer than a threshold figure.

## Taxonomy

The GBIF occurrence download will be organised according to the Catalogue of Life extended release (abbreviated as CoLXR), the new default for GBIF. 
Bachman 2024 uses the WCVP taxonomy (with IPNI as its nomenclatural layer), and is available for download from zenodo (https://zenodo.org/records/10605228). 

These two taxonomies can be reconciled by generating a mapping between the CoL extended release and IPNI using the checklistbank tool. This mapping is stored in the `resources` directory in the repository.


## Technical implementations

### Simple

#### Data access

Simple counts can be determined using the GBIF SQL download API with `GROUP BY` clauses, e.g.

```{sql}
SELECT occurrence.taxonKey, occurrence.datasetKey, COUNT(*) as c
FROM occurrence
WHERE occurrence.phylumKey  = 'TP' /* Tracheophyta */
    AND occurrence.basisofrecord = 'PRESERVED_SPECIMEN'
GROUP BY occurrence.taxonKey, occurrence.datasetKey
```

The resulting dataset is then:
1. Transformed from long format to wide, i.e. each row represents a different `taxonKey`, there is a column for each value of `datasetKey`, and the corresponding cells are the counts.
1. Augmented with threat predictions using the CoLXR - IPNI mapping
1. Summarised from the point of view of a particular institutional dataset

### Advanced (duplicate-aware)

GBIF processes occurrence records to determine "related records"; one category of relatedness is that two specimens are duplicates (originate from the same collecting event). The field `isincluster` in the occurrence table is a simple Boolean value, it requires a separate API call per occurrence to get the related occurrence IDs (see [GBIF API feature request](https://github.com/gbif/gbif-api/issues/228) for improved access to this data). As of September 2026, Kew has 6,162,811 occurrence records; of these 1,497,714 have related records. As resolution of related record links requires occurrence ID, the initial download cannot be pre-summarised as the simple example shown above. It will be necessary to work from the occurrence details for each of the records in the source dataset. (The number of occurrences in Tracheophyta with basisOfRecord set to PRESERVED_SPECIMEN is c 121 million as of September 2026, of these 26.7 million have related records) 

## Usage

### Running locally

The build process requires Python 3, GNU Make, zip and curl, install these and ensure that they are available on your PATH. 

On Windows, the `python` command must start Python 3; on Linux, the
Makefile uses `python3`. 

Run `make prep` to prepare the data or `make md` to generate the report. 

The first make run creates a virtual environment in `.venv` and installs the Python requirements, which are defined in `requirements.txt`.

### Continuous integration via github actions

The repository is configured to build using github actions, the build process can be initiated by pushing a change to the repository or by manually triggering a build from the actions tab in the github web user interface. 
The results and the formatted report are attached to the build as a zipfile named `build artifacts`.  

## Contributing
tbc
