import argparse
import pandas as pd

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Analyse GBIF specimens data")
    parser.add_argument("input_file_prepared", help="Input file (TSV, taxonomy=CoL)")
    parser.add_argument("--dataset_id", default='cd6e21c8-9e8a-493a-8a76-fbf7862069e5', help="Dataset ID for the institution's collection (default Kew)")
    parser.add_argument("output_file", help="Output CSV file")
    parser.add_argument("--log_level", default='INFO', help="Logging level (default INFO)")
    args = parser.parse_args()
    logger.setLevel(getattr(logging, args.log_level.upper()))

    logger.debug(f"Arguments: {args}")

    ###########################################################################
    # Prepare
    ###########################################################################

    # Read input files
    logger.info(f"Reading prepared data from {args.input_file_prepared}")
    df = pd.read_csv(args.input_file_prepared, sep='\t')
    logger.info(f"Prepared data shape: {df.shape}")

    # Set up analysis metadata so that we can run the same analysis for (1) all taxa and (2) just threatened taxa
    analyses = {'all_taxa': df, 
                'threatened_taxa': df[df['predicted_threat']=='threatened'],
                'not_threatened_taxa': df[df['predicted_threat']=='not threatened']}

    # Write markdown format report to output file
    with open(args.output_file, 'w') as f_out:
        f_out.write("# GBIF Specimens Analysis Report\n\n")
        f_out.write(f"Input file: {args.input_file_prepared}\n\n")
        f_out.write(f"Dataset ID: {args.dataset_id}\n\n")
        f_out.write("Species rank taxa only (no infraspecific taxa)\n\n")
        f_out.write(f"Run at {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for analysis_name, df_stats_analysis in analyses.items():
            f_out.write(f"## {analysis_name}\n")
            f_out.write("### Taxa\n")
            f_out.write(f"Total number: {len(df_stats_analysis)}\n")
            num_taxa_with_one_dataset = (df_stats_analysis['number_of_datasets_with_non_zero_counts'] == 1).sum()
            f_out.write(f"Number of taxa with only one dataset: {num_taxa_with_one_dataset}\n")
            num_taxa_with_inst_coll = (df_stats_analysis['dataset_count'] > 0).sum()
            f_out.write(f"Number of taxa with the institution's collection dataset present: {num_taxa_with_inst_coll}\n")
            num_taxa_with_inst_coll_only = ((df_stats_analysis['dataset_count'] > 0) & (df_stats_analysis['non_dataset_count'] == 0)).sum()
            f_out.write(f"Number of taxa with institutional collection (dataset {args.dataset_id}) as the only dataset: {num_taxa_with_inst_coll_only}\n")
            
            f_out.write("### Specimens\n")

            f_out.write(f"Number of specimens mobilised through GBIF: {df_stats_analysis['total_count'].sum()}\n")

            num_specimens_in_inst_coll = df_stats_analysis['dataset_count'].sum()
            f_out.write(f"Number of specimens in the institution's collection dataset: {num_specimens_in_inst_coll}\n")

            f_out.write("### Contribution of the target dataset to the total number of specimens for each taxon\n")
            # Collate percentage threshold data as a list of dicts to build pd dataframe 
            # (easier creation of markdown table)
            pc_threshold_data = []
            for percentage_threshold in [50,75,90,95,99,100]:
                mask = (df_stats_analysis['dataset_count_pc'] >= percentage_threshold)
                n_taxa_above_threshold = len(df_stats_analysis[mask])
                n_specimens_above_threshold = df_stats_analysis.loc[mask, 'dataset_count'].sum()    
                line_data = dict()
                line_data['percentage_threshold'] = percentage_threshold
                line_data['n_taxa_above_threshold'] = n_taxa_above_threshold
                line_data['n_specimens_above_threshold'] = n_specimens_above_threshold
                pc_threshold_data.append(line_data)

            df_pc_threshold = pd.DataFrame(pc_threshold_data)
            # Output df to markdown table
            f_out.write("\n")
            f_out.write(df_pc_threshold.to_markdown(index=False))
            f_out.write("\n\n")

            # horizontal line
            f_out.write("---\n\n")

if __name__ == "__main__":
    main()