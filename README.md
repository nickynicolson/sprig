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

The GBIF occurrence download will be organised according to the GBIF taxonomy. Bachman 2024 uses the WCVP taxonomy. These will need to be reconciled - see [querying GBIF resources by WCVP taxonomy](https://gist.github.com/nickynicolson/06369822ab6271d9ec0c8034e29eb8d7)

## Technical implementations

### Simple

#### Data access

Simple counts can be determined using the GBIF SQL download API with `GROUP BY` clauses, e.g.

```{sql}
SELECT occurrence.taxonKey, occurrence.datasetKey, COUNT(*) as c
FROM occurrence
WHERE CAST(occurrence.phylumKey AS INTEGER) = 7707728 /* Tracheophyta */
    AND occurrence.basisofrecord = 'PRESERVED_SPECIMEN'
GROUP BY occurrence.taxonKey, occurrence.datasetKey
```

The resulting dataset is then transformed from long format to wide, i.e. each row represents a different `taxonKey`, there is a column for each value of `datasetKey`, and the corresponding cells are the counts.

### Advanced (duplicate-aware)

GBIF processes occurrence records to determine "related records", one category of relatedness is that two specimens are duplicates (originate from the same collecting event). The field `isincluster` in the occurrence table is a simple Boolean value, it requires a separate API call per occurrence to get the related occurrence IDs. As of September 2026, Kew has 6,162,811 occurrence records; of these 1,497,714 have related records.

## Usage
tbc

## Contributing
tbc
