import argparse
import pandas as pd

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reshape(df, mask, index_col, columns_col, values_col, species_only=True):
    """
    Reshape a dataframe from long to wide format.
    :param df: Input dataframe in long format
    :param index_col: Column to use as the new index
    :param columns_col: Column to use as the new columns
    :param values_col: Column to use as the new values
    :return: Dataframe in wide format
    """

    logger.info("Reshaping GBIF data to wide format...")
    logger.info(f"Original GBIF data shape: {df.shape}")
    logger.info(f"Masked GBIF data shape: {df[mask].shape}")
    logger.info(f"Unique acceptedTaxonkeys at rank SPECIES: {df[mask]['acceptedtaxonkey'].nunique()}")
    logger.info(f"Unique datasetkeys: {df[mask]['datasetkey'].nunique()}")
    logger.info(f"Predicted shape of wide GBIF data: (acceptedtaxonkeys, datasetkeys) = ({df[mask]['acceptedtaxonkey'].nunique()}, {df[mask]['datasetkey'].nunique()}) ie {df[mask]['acceptedtaxonkey'].nunique() * df[mask]['datasetkey'].nunique()} cells")

    df_wide = df[mask][[index_col, columns_col, values_col]].pivot_table(index=index_col, columns=columns_col, values=values_col, aggfunc='sum')
    # Set NULL values to 0, as these indicate that there were no specimens for that taxonkey in that dataset
    df_wide.fillna(0, inplace=True)

    return df_wide

def add_columns(df, add_total_count=True, add_num_datasets=True, add_avg_count=True, add_std_count=True, inst_coll_dataset_id=None):

    # Remember the dataset columns
    logger.debug(f"Saving {len(df.columns)} dataset columns for later numerical calculations.")    
    dataset_columns = df.columns.tolist()

    # Record the names of the columns we add
    columns_added = []
    if add_total_count:
        # Add a column for the total count across all datasets
        logger.info("Calculating total_count across all datasets...")
        df['total_count'] = df[dataset_columns].sum(axis=1)
        df['total_count'] = df['total_count'].astype(int)  # Ensure total_count is an integer
        columns_added.append('total_count')
    if add_num_datasets:
    # Add a column for the number of datasets with non-zero counts
        logger.info("Calculating num_datasets with non-zero counts...")
        df['num_datasets'] = (df[dataset_columns] > 0).sum(axis=1)
        columns_added.append('num_datasets')
    if add_avg_count:
        # Add a column for the average count per dataset, constrain to 2 decimal places
        logger.info("Calculating avg_count per dataset...")
        # Should denominator be the number of datasets with non-zero counts, 
        # or the total number of datasets? 
        # We will use the total number of datasets, as this is more useful for our analysis.
        # df['avg_count'] = df['total_count'] / df['num_datasets']
        df['avg_count'] = df[dataset_columns].mean(axis=1)
        df['avg_count'] = df['avg_count'].round(2)
        columns_added.append('avg_count')
    if add_std_count:
        # Add a column for the standard deviation of the count per dataset
        # Constrain to 2 decimal places
        logger.info("Calculating SD of the count per dataset...")
        df['std_count'] = df[dataset_columns].std(axis=1)
        df['std_count'] = df['std_count'].round(2)
        columns_added.append('std_count')
    if inst_coll_dataset_id is not None:
        if inst_coll_dataset_id not in df.columns:
            logger.warning(f"Dataset ID {inst_coll_dataset_id} not found in the dataset columns. Please check the dataset ID and ensure it is present in the input data.")
        # Rename the datasetid column for the dataset of interest
        logger.info(f"Renaming dataset column {inst_coll_dataset_id} to target_inst_coll_count")
        df.rename(columns={inst_coll_dataset_id: 'target_inst_coll_count'}, inplace=True)
        df['target_inst_coll_count'] = df['target_inst_coll_count'].astype(int)  # Ensure target_inst_coll_count is an integer
        logger.debug(f"Non dataset-ID columns after renaming: {[col for col in df.columns.tolist() if col not in dataset_columns]}")
        columns_added.append('target_inst_coll_count')

        # Add a convenience column indicating whether the inst coll dataset is present for that taxonkey
        logger.info("Adding inst_coll_present column indicating whether the institution's collection dataset is nonzero for the current (taxon) row")
        df['inst_coll_present'] = df['target_inst_coll_count'] > 0
        columns_added.append('inst_coll_present')

        # Add a column for the specimen count NOT in the inst coll dataset
        logger.info("Adding other_inst_coll_count column indicating the specimen count NOT in the institution's collection dataset")
        df['other_inst_coll_count'] = df['total_count'] - df['target_inst_coll_count'] 
        df['other_inst_coll_count'] = df['other_inst_coll_count'].astype(int)  # Ensure other_inst_coll_count is an integer
        columns_added.append('other_inst_coll_count')

        # Add a column for the percentage of specimens in the inst coll dataset
        logger.info("Adding inst_coll_pc column indicating the percentage of specimens in the institution's collection dataset")
        df['inst_coll_pc'] = (df['target_inst_coll_count'] / df['total_count']) * 100
        df['inst_coll_pc'] = df['inst_coll_pc'].round(2)  # Constrain to 2 decimal places
        columns_added.append('inst_coll_pc')

    # Now drop all the other dataset columns, leaving only the summary columns and the target inst coll dataset column
    logger.info("Dropping all other dataset columns, leaving only the summary columns and the target inst coll dataset column")
    df = df[columns_added]
    # Reset index so that we have acceptedtaxonkey as a regular column
    df.reset_index(inplace=True)    

    return df

def extract_taxonomy(df, add_accepted_taxon_rank=True, add_predicted_threat=True, input_file_threat_mapping=None, threat_mapping_sep=None,species_only=False):
    # Extract taxonomy to separate dataframe
    
    if add_accepted_taxon_rank:
        # First we need to get the accepted taxon rank for each accepted taxon key.
        # Though we have a taxonrank column, this is populated with the rank of 
        # the provided scientificname. In the cases where the provided scientificname 
        # is a synonym, this rank may not be the rank of the accepted name. 
        # Therefore, we will build a mapping between taxonkey and taxonrank and 
        # apply this to the acceptedtaxonkey to create an acceptedtaxonrank column.
        df_taxon_key_rank_mapper = df[['taxonkey', 'taxonrank']].drop_duplicates()
        logger.info(f"Taxon key to rank mapping shape: {df_taxon_key_rank_mapper.shape}")
        logger.info(f"df shape BEFORE adding accepted taxon rank: {df.shape}")
        df = df.merge(df_taxon_key_rank_mapper, left_on='acceptedtaxonkey', right_on='taxonkey', how='left', suffixes=('', '_accepted'))
        logger.info(f"df shape AFTER adding accepted taxon rank: {df.shape}")
        df.rename(columns={'taxonrank_accepted': 'acceptedtaxonrank'}, inplace=True)


    # Extract taxonomy to separate dataframe
    taxonomy_columns = ['taxonkey', 'taxonrank', 'scientificname', 'acceptedtaxonkey', 'acceptedtaxonrank', 'acceptedscientificname']
    df_tax = df[taxonomy_columns].drop_duplicates().reset_index(drop=True)

    print(df_tax[df_tax.taxonkey.isin(['322F4'])].T)

    if add_predicted_threat:
        # Add predicted threat, which is mapped to taxonkey
        # The mapping file has columns: taxonkey, predicted_threat
        logger.info(f"Reading threat mapping data from {input_file_threat_mapping}")
        df_threat = pd.read_csv(input_file_threat_mapping, sep=threat_mapping_sep)
        print(df_threat.groupby('predicted_threat').size())
        print(df_threat.sample(n=1).T)
        logger.info(f"Threat mapping data shape: {df_threat.shape}")
        logger.info(f"Taxonomy data shape BEFORE merging with threat mapping: {df_tax.shape}")
        df_tax = df_tax.merge(df_threat, left_on='taxonkey', right_on='taxonkey', how='left')
        logger.info(f"Taxonomy data shape AFTER merging with threat mapping: {df_tax.shape}")
        print(df_tax.groupby('predicted_threat').size())
    if species_only:
        # We will only process things at the acceptedtaxonrank of SPECIES
        mask = (df_tax['acceptedtaxonkey'].notnull()) & (df_tax['acceptedtaxonrank'] == 'SPECIES')
        df_tax = df_tax[mask]
        logger.info(f"Taxonomy data shape AFTER filtering for acceptedtaxonrank=SPECIES: {df_tax.shape}")

    return df_tax

def integrate_data_frames(df_gbif_wide, df_tax, join_column='acceptedtaxonkey', jointype='left', drop_null_predicted_threat=True, threat_application_order = ('threatened', 'not threatened')):


    if drop_null_predicted_threat:
        # Drop any rows from df_tax where predicted_threat is null, as these are not useful for our analysis
        df_tax = df_tax[df_tax['predicted_threat'].notnull()]

    # If the difference in treatment of taxa between WCVP and CoL means that we have two predicted_threat values for the same taxon key
    # should we go with the threatened option or non-threatened?
    if not threat_application_order:
        threat_application_order = ['threatened', 'non-threatened']
    
    # Add accepted scientific name and rank from taxonomy dataframe
    logger.info(f"df_gbif_wide shape BEFORE merging with taxonomy data: {df_gbif_wide.shape}")
    df_gbif_wide = df_gbif_wide.merge(df_tax[['acceptedtaxonkey', 'acceptedscientificname', 'acceptedtaxonrank']].drop_duplicates(), left_on=join_column, right_on=join_column, how=jointype)
    logger.info(f"df_gbif_wide shape AFTER merging with taxonomy data: {df_gbif_wide.shape}")

    # Add an empty predicted_threat column to df_gbif_wide
    df_gbif_wide['predicted_threat'] = None
    for threat in threat_application_order:
        mask_tax = (df_tax['predicted_threat'] == threat)
        mask_gbif = (df_gbif_wide['predicted_threat'].isnull())
        # make a dictionary that maps acceptedtaxonkey to predicted_threat for the current threat value
        threat_mapping = df_tax[mask_tax].set_index('acceptedtaxonkey')['predicted_threat'].to_dict()
        # update the predicted_threat column in df_gbif_wide for rows where predicted_threat is null and the acceptedtaxonkey is in the threat_mapping dictionary
        df_gbif_wide.loc[mask_gbif & df_gbif_wide['acceptedtaxonkey'].isin(threat_mapping.keys()), 'predicted_threat'] = df_gbif_wide.loc[mask_gbif & df_gbif_wide['acceptedtaxonkey'].isin(threat_mapping.keys()), 'acceptedtaxonkey'].map(threat_mapping)
    
    logger.info(f"df_gbif_wide shape AFTER application of predicted threats: {df_gbif_wide.shape}")

    # How have we got duplicate rows for the same acceptedtaxonkey? 
    # Find out which acceptedtaxonkeys have more than one predicted threat value
    duplicates = df_gbif_wide[df_gbif_wide.duplicated(subset=['acceptedtaxonkey'], keep=False)]
    if not duplicates.empty:
        logger.info(f"Warning: {duplicates.shape[0]} duplicate rows found in GBIF data after merging with taxonomy data. This may indicate multiple predicted threat values for the same acceptedtaxonkey.")
        logger.debug(duplicates.sort_values(by=['acceptedtaxonkey', 'predicted_threat']))
        grouped_duplicates = duplicates.groupby('acceptedtaxonkey')
        for acceptedtaxonkey, group in grouped_duplicates:
            # if group contains more than one unique predicted threat value, print a warning
            if group['predicted_threat'].nunique() > 1:
                logger.debug(f"\nDuplicates for acceptedtaxonkey {acceptedtaxonkey}:")
                logger.debug(group[['acceptedscientificname', 'predicted_threat']])

    return df_gbif_wide

def main():
    parser = argparse.ArgumentParser(description="Prepare GBIF specimens data")
    parser.add_argument("input_file_gbif", help="Input summary GBIF specimen data (TSV, taxonomy=CoL)")
    parser.add_argument("--gbif_sep", default='\t', help="Separator for the GBIF file (default: tab)")
    parser.add_argument("input_file_threat_mapping", help="Input file taxonkey to predicted threat mapping (TSV)")
    parser.add_argument("--threat_mapping_sep", default='\t', help="Separator for the threat mapping file (default: comma)")
    parser.add_argument("--inst_coll_dataset_id", default='cd6e21c8-9e8a-493a-8a76-fbf7862069e5', help="Dataset ID for the institution's collection (default Kew)")
    parser.add_argument("output_file", help="Output CSV file")
    parser.add_argument("--log_level", default='INFO', help="Logging level (default INFO)")
    args = parser.parse_args()
    logger.setLevel(getattr(logging, args.log_level.upper()))

    logger.debug(f"Arguments: {args}")

    ###########################################################################
    # Prepare
    ###########################################################################

    # Read input files
    logger.info(f"Reading GBIF data from {args.input_file_gbif}")
    df_gbif = pd.read_csv(args.input_file_gbif, sep=args.gbif_sep)
    logger.info(f"GBIF data shape: {df_gbif.shape}")

    # This file was generated from a SQL query to aggregate counts
    # As we want to reshape, we will extract the taxonomy and store separately
    df_tax = extract_taxonomy(df_gbif, add_accepted_taxon_rank=True, add_predicted_threat=True, input_file_threat_mapping=args.input_file_threat_mapping, threat_mapping_sep=args.threat_mapping_sep, species_only=True)

    # We are only processing things at the acceptedtaxonrank of SPECIES
    mask = (df_gbif['acceptedtaxonkey'].isin(df_tax['acceptedtaxonkey']))


    # Now we have a long format dataframe with an acceptedtaxonkey column
    # As we may have multiple rows for the same acceptedtaxonkey and datasetkey, we will group by these two columns and sum the counts
    logger.info("Grouping GBIF data by acceptedtaxonkey and datasetkey and summing counts...")
    df_summary = df_gbif[mask].groupby(['acceptedtaxonkey', 'datasetkey'], as_index=False)['c'].sum()


    print('#'*80)
    print("Calculation strategy: algebraic summary")

    # 1. Define N (total unique datasets across your entire dataset collection)
    total_datasets = df_summary['datasetkey'].nunique() 

    # 2. Aggregate from your intermediate summed dataframe
    stats = df_summary.groupby('acceptedtaxonkey').agg(
        sum_c=('c', 'sum'),
        sum_c_sq=('c', lambda x: (x**2).sum()),
        non_zero_count=('datasetkey', 'count')
    ).reset_index()

    # 3. Compute zero-padded statistics algebraically
    stats['mean'] = stats['sum_c'] / total_datasets
    stats['sum'] = stats['sum_c']

    # Population variance & standard deviation (denominator = N)
    stats['variance'] = (stats['sum_c_sq'] / total_datasets) - (stats['mean'] ** 2)
    stats['std_dev'] = stats['variance'] ** 0.5

    # Sample variance (denominator = N - 1) if required:
    # stats['sample_variance'] = (stats['sum_c_sq'] - (stats['sum_c']**2 / total_datasets)) / (total_datasets - 1)
    
    # print algebraic summary statistics for a few sample taxa
    sample_taxa = ['5944Q', '322W5']
    for taxon in sample_taxa:
        if taxon in stats['acceptedtaxonkey'].values:
            row = stats[stats['acceptedtaxonkey'] == taxon]
            logger.info(f"Taxon ID {taxon}: mean={row['mean'].values[0]:.2f}, sum={row['sum'].values[0]}, std_dev={row['std_dev'].values[0]:.2f}, non_zero_count={row['non_zero_count'].values[0]}")
        else:
            logger.warning(f"Taxon ID {taxon} not found in algebraic summary statistics.") 

    # Add a flag column to indicate if the datasetkey is 
    # the one specified as the subject of the analysis

    df_summary['datasetkey_subject'] = df_summary['datasetkey'] == args.inst_coll_dataset_id
    # convert from bool to str
    df_summary['datasetkey_subject'] = df_summary['datasetkey_subject'].astype(str)
    df_wide = df_summary[['acceptedtaxonkey', 'datasetkey_subject', 'c']].pivot_table(index='acceptedtaxonkey', columns='datasetkey_subject', values='c', aggfunc='sum').fillna(0)
    # Rename columns
    print(df_wide.columns)
    df_wide.rename(columns = {'True':'dataset_count','False':'external_count'}, inplace=True)
    # df_wide = df[mask][[index_col, columns_col, values_col]].pivot_table(index=index_col, columns=columns_col, values=values_col, aggfunc='sum')

    df_stats = pd.merge(left=df_wide, right=stats, left_index=True, right_on="acceptedtaxonkey", how="left")
    sample_taxa = ['5944Q', '322W5']
    for taxon in sample_taxa:
        if taxon in df_stats['acceptedtaxonkey'].values:
            row = df_stats[df_stats['acceptedtaxonkey'] == taxon]
            logger.info(f"Taxon ID {taxon}: mean={row['mean'].values[0]:.2f}, sum={row['sum'].values[0]}, std_dev={row['std_dev'].values[0]:.2f}, non_zero_count={row['non_zero_count'].values[0]}, dataset_count={row['dataset_count'].values[0]}, external_count={row['external_count'].values[0]}")
        else:
            logger.warning(f"Taxon ID {taxon} not found in algebraic summary statistics.") 

    # # # Try to generate a link to look at the taxa in GBIF, using the accepted taxon keys
    # # if taxon_ids:
    # #     url = "https://www.gbif.org/occurrence/search?"
    # #     for taxon_id in taxon_ids:
    # #         url += f"taxonKey={taxon_id}&"
    # #     url += f"datasetKey={args.inst_coll_dataset_id}"
    # #     print(f"Link to view threatened taxa in GBIF: {url}")

    # Rename columns to be more descriptive
    df_stats.rename(columns={
        'external_count': 'non_dataset_count',
        'sum': 'total_count',
        'mean': 'avg_count',
        'std_dev': 'std_count',
        'non_zero_count': 'number_of_datasets_with_non_zero_counts'
    }, inplace=True)

    # Round stats columns to 2 dp
    df_stats['avg_count'] = df_stats['avg_count'].round(2)
    df_stats['std_count'] = df_stats['std_count'].round(2)
    df_stats['dataset_count_pc'] = (df_stats['dataset_count'] / df_stats['total_count']) * 100
    df_stats['dataset_count_pc'] = df_stats['dataset_count_pc'].round(2)  # Constrain to 2 decimal places

    # Analysis

    # Add taxonomic data
    df_stats = integrate_data_frames(df_stats, df_tax, join_column='acceptedtaxonkey', jointype='left', drop_null_predicted_threat=False)

    # Impose a sensible order on the columns for output
    # We have these columns available:
    # external_count	dataset_count	acceptedtaxonkey	sum_c	sum_c_sq	non_zero_count	mean	sum	variance	std_dev	acceptedscientificname	acceptedtaxonrank	predicted_threat	inst_coll_pc
    # We want first acceptedtaxonkey and assoc details, the predicted threat, the counts, inst_coll_pc and then the remaining stats columns
    preferred_column_order = ['acceptedtaxonkey', 'acceptedscientificname', 'acceptedtaxonrank', 'predicted_threat', 'dataset_count', 'non_dataset_count', 'dataset_count_pc', 'total_count', 'avg_count', 'std_count', 'number_of_datasets_with_non_zero_counts']
    df_stats = df_stats[preferred_column_order]

    # # Set up analysis metadata so that we can run the same analysis for (1) all taxa and (2) just threatened taxa
    # analyses = {'all_taxa': df_stats, 
    #             'threatened_taxa': df_stats[df_stats['predicted_threat']=='threatened'],
    #             'not_threatened_taxa': df_stats[df_stats['predicted_threat']=='not threatened']}

    # for analysis_name, df_stats_analysis in analyses.items():
    #     print(f"Running analysis for {analysis_name} at rank of species...")
    #     print("Taxa")
    #     print(f"Total number: {len(df_stats_analysis)}")
    #     num_taxa_with_one_dataset = (df_stats_analysis['non_zero_count'] == 1).sum()
    #     print(f"Number of taxa with only one dataset: {num_taxa_with_one_dataset}")
    #     num_taxa_with_inst_coll = (df_stats_analysis['dataset_count'] > 0).sum()
    #     print(f"Number of taxa with the institution's collection dataset present: {num_taxa_with_inst_coll}")
    #     num_taxa_with_inst_coll_only = ((df_stats_analysis['dataset_count'] > 0) & (df_stats_analysis['external_count'] == 0)).sum()
    #     print(f"Number of taxa with institutional collection (dataset {args.inst_coll_dataset_id}) as the only dataset: {num_taxa_with_inst_coll_only}")
        
    #     print('Specimens')
        
    #     print(f"Number of specimens mobilised through GBIF: {df_stats_analysis['sum'].sum()}")

    #     num_specimens_in_inst_coll = df_stats_analysis['dataset_count'].sum()
    #     print(f"Number of specimens in the institution's collection dataset: {num_specimens_in_inst_coll}")

    #     print('Contribution of the target dataset to the total number of specimens for each taxon')
    #     print('Percentage\tNumber of taxa\tNumber of specimens')
    #     # for percentage_threshold in [0.5, 0.75, 0.9, 0.95, 0.99, 1.0]:
    #     for percentage_threshold in [50,75,90,95,99,100]:
    #         mask = (df_stats_analysis['dataset_count_pc'] >= percentage_threshold)
    #         n_taxa_above_threshold = len(df_stats_analysis[mask])
    #         n_specimens_above_threshold = df_stats_analysis.loc[mask, 'dataset_count'].sum()    
    #         print(f"{percentage_threshold}%\t{n_taxa_above_threshold}\t{n_specimens_above_threshold}")

    #     print('-'*80)


    # Write prepared data to output file
    logger.info(f"Writing prepared data to output file {args.output_file}")
    df_stats.to_csv(args.output_file, index=False, sep='\t')

if __name__ == "__main__":
    main()