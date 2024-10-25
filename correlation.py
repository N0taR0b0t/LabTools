import pandas as pd
import numpy as np
import plotly.figure_factory as ff
import plotly.io as pio
import chardet
import matplotlib.colors as mcolors
import matplotlib.cm as cm

# Function to detect file encoding
def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        result = chardet.detect(file.read(100000))  #Bytes for detection
        return result['encoding']

# Function to calculate luminance of a color (0 = dark, 1 = light)
def calculate_luminance(rgb):
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b

# Function to get RGB from colorscale
def get_rgb_from_colorscale(value, vmin, vmax, colorscale='RdBu'):
    norm_value = (value - vmin) / (vmax - vmin)  # Normalize value between 0 and 1
    cmap = cm.get_cmap(colorscale)
    rgba = cmap(norm_value)
    rgb = mcolors.to_rgb(rgba)
    return rgb

# Function to determine text color based on background color luminance
def get_text_color_by_luminance(value, vmin, vmax, threshold=0.5):
    if np.isnan(value):
        return "black"
    rgb = get_rgb_from_colorscale(value, vmin, vmax)
    luminance = calculate_luminance(rgb)
    return "white" if luminance < threshold else "black"

# Function to generate the correlation heatmap and save as HTML
def generate_correlation_heatmap_html(file_path, output_html, threshold=0.5):
    # Detect the encoding of the CSV file
    encoding = detect_encoding(file_path)
    
    # Load the CSV file using the detected encoding
    data = pd.read_csv(file_path, encoding=encoding)

    # Select the 'Ratio' columns
    ratio_columns = [col for col in data.columns if col.startswith('Ratio:')]

    # Ensure these columns are numeric and drop rows with NaN values
    ratio_data = data[ratio_columns].apply(pd.to_numeric, errors='coerce')
    cleaned_ratio_data = ratio_data.dropna()

    # Compute the correlation matrix
    corr_matrix = cleaned_ratio_data.corr()

    # Remove diagonal (self-correlations) by setting them to NaN
    corr_matrix_no_diag = corr_matrix.copy()
    np.fill_diagonal(corr_matrix_no_diag.values, np.nan)

    # Mask the upper triangle (since the matrix is symmetrical)
    mask = np.triu(np.ones_like(corr_matrix_no_diag, dtype=bool))

    # Apply the mask to hide the upper half of the matrix and keep the lower triangle
    corr_matrix_masked = corr_matrix_no_diag.mask(mask)

    # Replace NaNs in the correlation matrix (diagonal and masked cells) with empty strings
    z_values = corr_matrix_masked.values
    annotation_text = np.where(np.isnan(z_values), "", np.round(z_values, 2).astype(str))

    # Get the min and max of the remaining values to normalize the color map
    vmin = np.nanmin(z_values)
    vmax = np.nanmax(z_values)

    # Use the full gradient from blue to red
    colorscale = 'RdBu'  # Continuous gradient from blue to red

    # Create the heatmap figure using Plotly
    fig = ff.create_annotated_heatmap(
        z=z_values,
        x=corr_matrix.columns.tolist(),
        y=corr_matrix.index.tolist(),
        annotation_text=annotation_text,
        colorscale=colorscale,
        showscale=True,
        zmin=vmin,
        zmax=vmax,
        hoverinfo="z"
    )

    # Apply the text color to each annotation based on their x and y positions
    for annotation in fig.layout.annotations:
        # Get the x (column) and y (row) labels
        x_label = annotation.x
        y_label = annotation.y

        # Find the corresponding row and column indices
        try:
            row = corr_matrix.index.tolist().index(y_label)
            col = corr_matrix.columns.tolist().index(x_label)
        except ValueError:
            # If label not found, default to black
            annotation.font.color = "black"
            print(f"Label not found for X: {x_label}, Y: {y_label}. Setting Text Color: black")
            continue

        # Get the corresponding z_value
        if row < z_values.shape[0] and col < z_values.shape[1]:
            value = z_values[row][col]
            color = get_text_color_by_luminance(value, vmin, vmax, threshold)
            annotation.font.color = color
            # Debugging: Print the mapping and color decision
            print(f"Row: {row}, Column: {col}, Value: {value}, Text Color: {color}")
        else:
            annotation.font.color = "black"
            print(f"Row: {row}, Column: {col}, Out of bounds. Setting Text Color: black")

    # Update layout to make it visually appealing and remove grid lines
    fig.update_layout(
        title_text="Correlation Heatmap of Ratio Columns",
        title_x=0.5,
        font=dict(family="Arial, sans-serif", size=12, color="black"),
        xaxis=dict(showgrid=False, side="bottom"),  # Disable grid lines on x-axis
        yaxis=dict(showgrid=False, autorange="reversed"),  # Disable grid lines on y-axis
        plot_bgcolor="white",
        paper_bgcolor="white"
    )

    # Save the heatmap as an HTML file
    pio.write_html(fig, file=output_html, auto_open=False, full_html=True)

    print(f"HTML file '{output_html}' generated with the improved correlation heatmap.")

# File path to the CSV file (update this to your actual file path)
file_path = 'LiverF.csv'

# Output HTML file path
output_html = 'correlation.html'

# Optional: Define a threshold for luminance-based text color
threshold = 0.5

# Run the function to generate the heatmap
generate_correlation_heatmap_html(file_path, output_html, threshold)