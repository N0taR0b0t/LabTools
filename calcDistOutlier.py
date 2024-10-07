import pandas as pd
import numpy as np
from collections import defaultdict

# List of file names
files = [
    "cla-lps_ctrl.csv", "no2-cla_ctrl.csv", "cla-lps_lps.csv", 
    "lps_ctrl.csv", "cla_ctrl.csv", "no2-cla-lps_lps.csv"
]

REMOVE_OUTLIER = False

# Initialize a dictionary to store the cumulative distances for each compound
compound_distances = defaultdict(list)
outlier_detected_files = defaultdict(list)

# List of relevant columns to process
# TODO: Replace hard coded columns
comparisons = [
    ("Log2 Fold Change: (cla) / (ctrl)", "P-value: (cla) / (ctrl)"),
    ("Log2 Fold Change: (cla/lps) / (ctrl)", "P-value: (cla/lps) / (ctrl)"),
    ("Log2 Fold Change: (lps) / (ctrl)", "P-value: (lps) / (ctrl)"),
    ("Log2 Fold Change: (no2-cla/lps) / (ctrl)", "P-value: (no2-cla/lps) / (ctrl)"),
    ("Log2 Fold Change: (cla/lps) / (lps)", "P-value: (cla/lps) / (lps)"),
    ("Log2 Fold Change: (no2-cla/lps) / (lps)", "P-value: (no2-cla/lps) / (lps)")
]

# Process each file
for file in files:
    # Load the CSV file into a DataFrame with appropriate encoding
    df = pd.read_csv(file, encoding='ISO-8859-1')
    
    # Process each comparison
    for log2fc_col, pval_col in comparisons:
        if log2fc_col in df.columns and pval_col in df.columns:
            # Calculate -log10(p-value)
            df['-log10(p-value)'] = -np.log10(df[pval_col])
            
            # Filter rows where 'Checked' is True
            checked_df = df[df['Checked'] == True]
            
            # Find leftmost, rightmost, and topmost points
            leftmost_x = checked_df[log2fc_col].min()
            rightmost_x = checked_df[log2fc_col].max()
            topmost_y = checked_df['-log10(p-value)'].max()
            
            # Iterate over each checked compound to calculate distances
            for index, row in checked_df.iterrows():
                x = row[log2fc_col]
                y = row['-log10(p-value)']
                
                # Calculate the distance
                if x < 0:
                    distance = np.sqrt((x - leftmost_x) ** 2 + (y - topmost_y) ** 2)
                else:
                    distance = np.sqrt((x - rightmost_x) ** 2 + (y - topmost_y) ** 2)
                
                # Add this distance to the list for this compound
                compound_id = row['Compounds ID']
                compound_distances[compound_id].append((distance, file))

# Process compound distances, detecting outliers and optionally removing them
final_distances = {}

for compound_id, distance_file_pairs in compound_distances.items():
    distances = np.array([pair[0] for pair in distance_file_pairs])
    files_list = [pair[1] for pair in distance_file_pairs]
    
    if len(distances) > 1:
        # Calculate the median and MAD (Median Absolute Deviation)
        median = np.median(distances)
        mad = np.median(np.abs(distances - median))
        
        # Avoid division by zero in MAD calculation
        if mad == 0:
            mad = np.std(distances)
        
        # Calculate modified Z-scores
        modified_z_scores = 0.6745 * (distances - median) / mad
        
        # Identify the most significant outlier
        max_z_index = np.argmax(np.abs(modified_z_scores))
        detected_file = files_list[max_z_index]
        
        # Track the file where the outlier was detected
        outlier_detected_files[compound_id].append(detected_file)
        
        if REMOVE_OUTLIER:
            # Remove the most significant outlier
            filtered_distances = np.delete(distances, max_z_index)
            files_list = np.delete(files_list, max_z_index).tolist()
        else:
            filtered_distances = distances
    else:
        filtered_distances = distances
    
    # Calculate the weighted average distance (weights are inversely proportional to the variance)
    if len(filtered_distances) > 1:
        weights = 1 / np.var(filtered_distances)
        final_distance = np.average(filtered_distances, weights=np.full_like(filtered_distances, weights))
    else:
        final_distance = filtered_distances[0]
    
    final_distances[compound_id] = final_distance

# Convert the distances dictionary to a DataFrame
compound_distance_df = pd.DataFrame.from_dict(final_distances, orient='index', columns=['Total Distance'])

# Load the mapping for compound IDs to Names and Calc. MW from one of the files
mapping_df = pd.read_csv(files[0], encoding='ISO-8859-1')

# Map Compound IDs to Names and Calc. MW, and handle NaN in Names
mapping = mapping_df[['Compounds ID', 'Name', 'Calc. MW']].drop_duplicates()
mapping['Name'] = mapping['Name'].fillna(mapping['Calc. MW'])

# Merge the distances with the mapping
compound_distance_named_df = compound_distance_df.merge(mapping, left_index=True, right_on='Compounds ID')

# Add information about where outliers were detected, if applicable
compound_distance_named_df['Outlier Detected In'] = compound_distance_named_df['Compounds ID'].map(outlier_detected_files)

# Select only relevant columns: Name, Total Distance, and Outlier Detected In
final_result = compound_distance_named_df[['Name', 'Total Distance', 'Outlier Detected In']].sort_values(by='Total Distance')

# Display the top 50 compounds by total distance with names
print(final_result.head(50))

# Optionally, save the final result to a CSV file
final_result.to_csv('significant_compounds_by_distance_named_v5.csv', index=False)
