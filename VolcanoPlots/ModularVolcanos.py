import pandas as pd
import plotly.graph_objects as go
import numpy as np
import chardet

# Function to detect file encoding
def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        result = chardet.detect(file.read(100000))  # Read the first 100000 bytes for detection
        return result['encoding']

# File path to the CSV
file_path = '/Users/matias/Library/Mobile Documents/com~apple~CloudDocs/Work/LiverF/LiverF.csv'

# Detect the encoding of the CSV file
encoding = detect_encoding(file_path)

# Load the CSV file using the detected encoding
by_distance_named = pd.read_csv(file_path, encoding=encoding)

# Ensure 'Calc. MW' is numeric
by_distance_named['Calc. MW'] = pd.to_numeric(by_distance_named['Calc. MW'], errors='coerce')

# Extract the list of Calc. MW to be highlighted in gold (ensure only 50 masses)
gold_masses = by_distance_named['Calc. MW'].dropna().head(50).tolist()

# Function to automatically detect fold change and p-value columns
def detect_columns(dataframe):
    fold_change_columns = [col for col in dataframe.columns if col.startswith('Log2 Fold Change:')]
    p_value_columns = [col for col in dataframe.columns if col.startswith('P-value:')]
    
    # Pair the detected columns based on matching experiment names after the prefixes
    detected_columns = {}
    for fc_col in fold_change_columns:
        experiment = fc_col.replace('Log2 Fold Change: ', '')
        for p_col in p_value_columns:
            if p_col.replace('P-value: ', '') == experiment:
                detected_columns[experiment] = {
                    'fold_change_col': fc_col,
                    'p_value_col': p_col,
                    'title': f'Volcano Plot: {experiment}'
                }
    return detected_columns

# Automatically detect the columns and their titles
files_and_columns = detect_columns(by_distance_named)

# Initialize the figure
fig = go.Figure()

# List to store per-experiment data
experiments_data = []

# Track the traces and buttons for the dropdown
dropdown_buttons = []
for i, (experiment, params) in enumerate(files_and_columns.items()):
    # Use the data from 'by_distance_named' directly
    data = by_distance_named.copy()
    
    # Ensure necessary columns exist, and replace NaN with empty strings
    data['Name'] = data['Name'].fillna('[-]')
    data['Formula'] = data['Formula'].fillna('[-]')
    data['Calc. MW'] = pd.to_numeric(data['Calc. MW'], errors='coerce')
    data['m/z'] = data['m/z'].fillna('')
    data['RT [min]'] = data['RT [min]'].fillna('')
    
    # Convert fold change and p-value columns to numeric
    data[params['fold_change_col']] = pd.to_numeric(data[params['fold_change_col']], errors='coerce')
    data[params['p_value_col']] = pd.to_numeric(data[params['p_value_col']], errors='coerce')
    
    # Drop rows with NaN values in fold change or p-value columns
    data = data.dropna(subset=[params['fold_change_col'], params['p_value_col']])
    
    # Create a new column for -log10(P-value)
    data['-Log10(P-value)'] = -np.log10(data[params['p_value_col']])
    
    # Determine conditions for coloring points
    significant_upregulated = (data[params['fold_change_col']] > 0.5) & (data[params['p_value_col']] < 0.05)
    significant_downregulated = (data[params['fold_change_col']] < -0.5) & (data[params['p_value_col']] < 0.05)
    
    # Create a color column
    data['Color'] = 'blue'  # Default color
    data.loc[significant_upregulated, 'Color'] = 'green'
    data.loc[significant_downregulated, 'Color'] = 'red'
    data.loc[data['Calc. MW'].isin(gold_masses), 'Color'] = 'gold'  # Gold color for specific masses
    
    # Modify hovertext to include the additional columns
    hover_text = (
        "Name:\t" + data['Name'].astype(str) + "<br>" +
        "Formula:\t" + data['Formula'].astype(str) + "<br>" +
        "Calc. MW:\t" + data['Calc. MW'].astype(str) + "<br>" +
        "m/z:\t" + data['m/z'].astype(str) + "<br>" +
        "RT [min]:\t" + data['RT [min]'].astype(str)
    )
    
    # Compute maximum absolute fold change value
    max_abs_x = data[params['fold_change_col']].abs().max()
    # Extend it by 10%
    max_x = max_abs_x * 1.1
    # Set symmetric x-axis limits
    x_min = -max_x
    x_max = max_x
    
    # Compute y-axis limits
    y_values = data['-Log10(P-value)']
    y_max = y_values.max()
    y_range = y_max
    y_max += 0.1 * y_range  # Extend y_max by 10%
    
    # Create shapes
    shapes = [
        # Horizontal line at y = -log10(0.05)
        dict(
            type="line",
            x0=x_min,
            x1=x_max,
            y0=-np.log10(0.05),
            y1=-np.log10(0.05),
            line=dict(color="Black", dash="dash")
        ),
        # Vertical line at x = -0.5
        dict(
            type="line",
            x0=-0.5,
            x1=-0.5,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="Black", dash="dash")
        ),
        # Vertical line at x = 0.5
        dict(
            type="line",
            x0=0.5,
            x1=0.5,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="Black", dash="dash")
        )
    ]
    
    # Append experiment data to the list
    experiments_data.append({
        'x_min': x_min,
        'x_max': x_max,
        'y_max': y_max,
        'shapes': shapes
    })
    
    fig.add_trace(go.Scatter(
        x=data[params['fold_change_col']],
        y=data['-Log10(P-value)'],
        mode='markers',
        marker=dict(color=data['Color'], opacity=0.9),
        hovertext=hover_text,
        hoverinfo='text',
        visible=True if i == 0 else False,  # Make the first plot visible
        name="Key",
        hoverlabel=dict(
            font_size=16,
            font_family="Arial",
            bgcolor="red",
            bordercolor="black",
        )
    ))
    
    # Add dropdown button for this dataset
    dropdown_buttons.append(dict(
        method="update",
        label=params['title'],
        args=[
            {"visible": [j == i for j in range(len(files_and_columns))] + [True] * 4},  # Keep legend visible
            {"title": params['title'],
             "xaxis": {"title": params['fold_change_col'], "range": [x_min, x_max]},
             "yaxis": {"title": f"-Log10({params['p_value_col']})", "range": [0, y_max]},
             "shapes": shapes}
        ]
    ))

# Add key for the colors (gold, green, red, blue)
color_legend = [
    go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=12, color='gold'),
        showlegend=True,
        name='50 Lowest Average Distances',
        visible=True
    ),
    go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=12, color='green'),
        showlegend=True,
        name='Significant Upregulated',
        visible=True
    ),
    go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=12, color='red'),
        showlegend=True,
        name='Significant Downregulated',
        visible=True
    ),
    go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=12, color='blue'),
        showlegend=True,
        name='Insignificant',
        visible=True
    )
]

# Add the color legend to the figure
for legend_trace in color_legend:
    fig.add_trace(legend_trace)

# Add dropdown menu to layout
fig.update_layout(
    updatemenus=[
        dict(
            buttons=dropdown_buttons,
            direction="down",
            pad={"r": 10, "t": 10},
            showactive=True,
            x=1.15,
            xanchor="right",
            y=1.15,
            yanchor="top"
        )
    ]
)

# Set initial layout for the plot
initial_experiment = list(files_and_columns.keys())[0]
initial_data = experiments_data[0]

fig.update_layout(
    title=files_and_columns[initial_experiment]['title'],
    xaxis_title=files_and_columns[initial_experiment]['fold_change_col'],
    yaxis_title=f"-Log10({files_and_columns[initial_experiment]['p_value_col']})",
    xaxis=dict(range=[initial_data['x_min'], initial_data['x_max']]),
    yaxis=dict(range=[0, initial_data['y_max']]),
    shapes=initial_data['shapes'],
    plot_bgcolor="lightslategray",
    paper_bgcolor="lightslategray",
    font=dict(color="black")
)

# Enable grid lines
fig.update_xaxes(showgrid=True)
fig.update_yaxes(showgrid=True)

# Save the plot as an HTML file
fig.write_html("volcano_plot.html")
