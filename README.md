# sprig
specimen prioritisation rules for institutional georeferencing

## Rationale

This repository defines a SQL format download from GBIF and processes it for use in the prioritisation of specimens for georeferencing within an institutional collection. 

It is intended for use by the institutional holder of a particular specimen collection.

## Prioritisation criteria

1. Specimen represents a species that is assessed as threatened according to [Bachman 2024](https://doi.org/10.1111/nph.19592)
2. Specimens of species where the GBIF occurrence holdings are entirely (or majority) drawn from the institutional collection.
3. Specimens of species with fewer than a threshold figure.

## Taxonomy

The GBIF occurrence download will be organised according to the Catalogue of Life extended release, the new default for GBIF. Bachman 2024 uses the WCVP taxonomy, and is available for download from zenodo (https://zenodo.org/records/10605228). These will need to be reconciled. Since WCVP uses IPNI as its nomenclatural layer, and it is possible to query the GBIF species API by name identifier from IPNI, we can build a mapping between the GBIF occurrences and the WCVP/IPNI labelled threat predictions. A sample v2 API query by IPNI name ID, returning the new CoLXR key is shown here:
```bash
curl -X 'GET' \
  'https://api.gbif.org/v2/species/match?scientificNameID=urn:lsid:ipni.org:names:77103633-1&checklistKey=7ddf754f-d193-4cc9-b351-99906754a03b' \
  -H 'accept: application/json' \
  -H 'Accept-Language: en'
```

```json
{
  "usage": {
    "key": "4XZLL",
    "name": "Solanum aspersum S.Knapp",
    "canonicalName": "Solanum aspersum",
    "authorship": "S.Knapp",
    "rank": "SPECIES",
    "code": "BOTANICAL",
    "status": "ACCEPTED",
    "genericName": "Solanum",
    "specificEpithet": "aspersum",
    "type": "SCIENTIFIC",
    "formattedName": "\u003Ci\u003ESolanum\u003C/i\u003E \u003Ci\u003Easpersum\u003C/i\u003E S.Knapp"
  },
  "classification": [
    {
      "key": "CS5HF",
      "name": "Eukaryota",
      "rank": "DOMAIN"
    },
    {
      "key": "P",
      "name": "Plantae",
      "rank": "KINGDOM"
    },
    {
      "key": "CMQ8S",
      "name": "Pteridobiotina",
      "rank": "SUBKINGDOM"
    },
    {
      "key": "TP",
      "name": "Tracheophyta",
      "rank": "PHYLUM"
    },
    {
      "key": "MG",
      "name": "Magnoliopsida",
      "rank": "CLASS"
    },
    {
      "key": "43W",
      "name": "Solanales",
      "rank": "ORDER"
    },
    {
      "key": "626XM",
      "name": "Solanaceae",
      "rank": "FAMILY"
    },
    {
      "key": "628NX",
      "name": "Solanoideae",
      "rank": "SUBFAMILY"
    },
    {
      "key": "KVSD2",
      "name": "Solaneae",
      "rank": "TRIBE"
    },
    {
      "key": "63SD9",
      "name": "Solanum",
      "rank": "GENUS"
    },
    {
      "key": "4XZLL",
      "name": "Solanum aspersum",
      "rank": "SPECIES"
    }
  ],
  "diagnostics": {
    "matchType": "EXACT",
    "confidence": 100,
    "timeTaken": 2,
    "timings": {
      "idMatchScientificNameID": 2,
      "sciNameMatch": 0,
      "checkScientificNameAndIDConsistencyScientificNameID": 0,
      "checkConsistencyWithClassificationMatch": 0
    },
    "matchedID": {
      "id": "77103633-1",
      "mainIndexID": "4XZLL",
      "datasetKey": "046bbc50-cae2-47ff-aa43-729fbf53f7c5",
      "clbDatasetKey": "2006",
      "datasetTitle": "International Plant Names Index (IPNI)",
      "parentID": "30000631-2",
      "scientificName": "Solanum aspersum S.Knapp",
      "rank": "SPECIES",
      "status": "PROVISIONALLY_ACCEPTED",
      "recognizedVariants": [
        "urn:lsid:ipni.org:names:77103633-1",
        "ipni:77103633-1",
        "https://www.ipni.org/n/77103633-1"
      ]
    }
  },
  "synonym": false,
  "left": 1364801,
  "right": 1364801
}
```
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

The resulting dataset is then transformed from long format to wide, i.e. each row represents a different `taxonKey`, there is a column for each value of `datasetKey`, and the corresponding cells are the counts.

### Advanced (duplicate-aware)

GBIF processes occurrence records to determine "related records"; one category of relatedness is that two specimens are duplicates (originate from the same collecting event). The field `isincluster` in the occurrence table is a simple Boolean value, it requires a separate API call per occurrence to get the related occurrence IDs. As of September 2026, Kew has 6,162,811 occurrence records; of these 1,497,714 have related records. As resolution of related record links requires occurrence ID, the initial download cannot be pre-summarised as the simple example shown above. It will be necessary to work from the occurrence details for each of the records in the source dataset. (The number of occurrences in Tracheophyta with basisOfRecord set to PRESERVED_SPECIMEN is c 121 million as of September 2026, of these 26.7 million have related records) 

## Usage
tbc

## Contributing
tbc
