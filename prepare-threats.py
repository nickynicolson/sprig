import argparse
import pandas as pd

'''
Prepare WCVP/IPNI threat predictions data for merging with GBIF specimens data by integrating
with the IPNI-CoL ID mapping data. 
The script reads in the threat predictions and mapping files, merges them to associate threat 
data with accepted taxon keys, and outputs a CSV file with the prepared data.
'''
def main():
    parser = argparse.ArgumentParser(description="Prepare WCVP/IPNI threat predictions data")
    parser.add_argument("input_file_threat", help="Input threat predictions data (CSV, taxonomy=WCVP/IPNI)")
    parser.add_argument("input_file_mapping", help="Input IPNI-CoL ID mapping data (TSV)")
    parser.add_argument("output_file", help="Output TSV file")
    args = parser.parse_args()

    # Read in the threat predictions data
    df_threat = pd.read_csv(args.input_file_threat, usecols=['ipni_id', 'predicted_threat', 'taxon_name'])
    df_threat.rename(columns={'ipni_id': 'ipni_id', 'predicted_threat':'predicted_threat', 'taxon_name':'wcvp_taxon_name'}, inplace=True)
    print("Threat data shape:", df_threat.shape)

    # Drop any rows with null IPNI IDs or predicted threat values, as these are not useful for our analysis
    df_threat = df_threat[df_threat['ipni_id'].notnull() & df_threat['predicted_threat'].notnull()]
    print("Threat data shape after dropping rows with null IPNI IDs or predicted threat values:", df_threat.shape)

    # Sanity check that each IPNI ID has only one predicted threat value
    duplicates = df_threat[df_threat.duplicated(subset=['ipni_id'], keep=False)]
    if not duplicates.empty:
        print(f"Warning: {duplicates.shape[0]} duplicate rows found in threat data. This may indicate multiple threat predictions for the same IPNI ID.")
        print(duplicates)

    # Add mapping information to the threat data so that it is suitable for integration with specimen data

    # The mapping file has columns: original_ID, ID, scientificName, acceptedID, acceptedScientificName
    df_mapping = pd.read_csv(args.input_file_mapping, usecols=['original_ID', 'matchType', 'ID', 'scientificName', 'acceptedID', 'acceptedScientificName'], sep='\t')
    df_mapping.rename(columns={'original_ID': 'ipni_id', 'ID':'taxonkey', 'acceptedID':'acceptedtaxonkey'}, inplace=True)
    print("Mapping data shape:", df_mapping.shape)

    # Only keep rows where the matchType is 'exact', as these are the most reliable mappings
    df_mapping = df_mapping[df_mapping['matchType'] == 'exact']
    print("Mapping data shape after filtering for exact matches:", df_mapping.shape)

    # Copy taxonkey to acceptedtaxonkey where acceptedtaxonkey is null, as this indicates that the original ID is already the accepted ID
    df_mapping['acceptedtaxonkey'] = df_mapping.apply(lambda row: row['taxonkey'] if pd.isnull(row['acceptedtaxonkey']) else row['acceptedtaxonkey'], axis=1)

    # drop any mapping rows where the acceptedtaxonkey is null, as these are not useful for our analysis
    df_mapping = df_mapping[df_mapping['acceptedtaxonkey'].notnull()]
    print("Mapping data shape after dropping rows with null acceptedtaxonkey:", df_mapping.shape)


    # Add mapping information to the threat data
    df_threat = df_threat.merge(df_mapping[['ipni_id','taxonkey']].drop_duplicates(), left_on='ipni_id', right_on='ipni_id', how='inner')


    print('-'*80)
    dfg = df_threat[['predicted_threat','taxonkey']].drop_duplicates().groupby('taxonkey').count()
    print(dfg[dfg['predicted_threat'] > 1])
    print('-'*80)

    df_out = df_threat[['taxonkey', 'predicted_threat']].drop_duplicates()

    # Any duplicate taxonkeys that remain must have conflicting predicted threat values
    # so we will flag as unresolvable
    if df_out.duplicated(subset=['taxonkey'], keep=False).any():
        print("Warning: Duplicate taxonkeys found in the output data. This may indicate conflicting predicted threat values for the same taxonkey.")
        duplicates = df_out[df_out.duplicated(subset=['taxonkey'], keep=False)]
        print(duplicates.sort_values(by=['taxonkey', 'predicted_threat']))
        # Add a column to the output data to flag these duplicates
        df_out['duplicate_flag'] = df_out.duplicated(subset=['taxonkey'], keep=False)
    else:
        df_out['duplicate_flag'] = False

    print(df_out.groupby('duplicate_flag').size())

    # Write prepared data to output file
    df_out.to_csv(args.output_file, index=False, sep='\t')

if __name__ == "__main__":
    main()