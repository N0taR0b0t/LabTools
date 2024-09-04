import pandas as pd
import plotly.graph_objects as go
import numpy as np

# Load the by_distance_named.csv file
by_distance_named = pd.read_csv('/Users/matias/Library/Mobile Documents/com~apple~CloudDocs/Work/NewRatios/by_distance_named.csv')
gold_masses = by_distance_named['Calc. MW'].tolist()  # Extract the list of Calc. MW to be highlighted in gold

# Define the files and corresponding column names
files_and_columns = {
    'cla-lps_ctrl.csv': {
        'fold_change_col': "Log2 Fold Change: (cla/lps) / (ctrl)",
        'p_value_col': "P-value: (cla/lps) / (ctrl)",
        'title': "Volcano Plot: CLA/LPS vs CTRL"
    },
    'cla-lps_lps.csv': {
        'fold_change_col': "Log2 Fold Change: (cla/lps) / (lps)",
        'p_value_col': "P-value: (cla/lps) / (lps)",
        'title': "Volcano Plot: CLA/LPS vs LPS"
    },
    'cla_ctrl.csv': {
        'fold_change_col': "Log2 Fold Change: (cla) / (ctrl)",
        'p_value_col': "P-value: (cla) / (ctrl)",
        'title': "Volcano Plot: CLA vs CTRL"
    },
    'lps_ctrl.csv': {
        'fold_change_col': "Log2 Fold Change: (lps) / (ctrl)",
        'p_value_col': "P-value: (lps) / (ctrl)",
        'title': "Volcano Plot: LPS vs CTRL"
    },
    'no2-cla-lps_lps.csv': {
        'fold_change_col': "Log2 Fold Change: (no2-cla/lps) / (lps)",
        'p_value_col': "P-value: (no2-cla/lps) / (lps)",
        'title': "Volcano Plot: NO2-CLA/LPS vs LPS"
    },
    'no2-cla_ctrl.csv': {
        'fold_change_col': "Log2 Fold Change: (no2-cla/lps) / (ctrl)",
        'p_value_col': "P-value: (no2-cla/lps) / (ctrl)",
        'title': "Volcano Plot: NO2-CLA/LPS vs CTRL"
    }
}

# Initialize the figure
fig = go.Figure()

# Track the traces and buttons for the dropdown
dropdown_buttons = []
for i, (file, params) in enumerate(files_and_columns.items()):
    # Load the CSV file
    data = pd.read_csv(file, encoding='ISO-8859-1')

    # Ensure necessary columns exist, and replace NaN with empty strings
    data['Name'] = data['Name'].fillna('[-]')
    data['Formula'] = data['Formula'].fillna('[-]')
    data['Calc. MW'] = data['Calc. MW'].fillna('')
    data['m/z'] = data['m/z'].fillna('')
    data['RT [min]'] = data['RT [min]'].fillna('')

    # Create a new column for -log10(P-value)
    data['-Log10(P-value)'] = -np.log10(data[params['p_value_col']])

    # Determine conditions for coloring points
    significant_upregulated = (data[params['fold_change_col']] > 0.5) & (data[params['p_value_col']] < 0.05)
    significant_downregulated = (data[params['fold_change_col']] < -0.5) & (data[params['p_value_col']] < 0.05)
    insignificant = ~significant_upregulated & ~significant_downregulated

    # Create a color column and set color to gold if Calc. MW matches one from by_distance_named.csv
    data['Color'] = np.where(data['Calc. MW'].isin(gold_masses), 'gold',
                             np.where(significant_upregulated, 'green',
                                      np.where(significant_downregulated, 'red', 'blue')))

    # Modify hovertext to include the additional columns with tab formatting
    hover_text = (
        "Name:\t" + data['Name'].astype(str) + "<br>" +
        "Formula:\t" + data['Formula'].astype(str) + "<br>" +
        "Calc. MW:\t" + data['Calc. MW'].astype(str) + "<br>" +
        "m/z:\t" + data['m/z'].astype(str) + "<br>" +
        "RT [min]:\t" + data['RT [min]'].astype(str)
    )

    fig.add_trace(go.Scatter(
        x=data[params['fold_change_col']],
        y=data['-Log10(P-value)'],
        mode='markers',
        marker=dict(color=data['Color'], opacity=0.9),
        hovertext=hover_text,
        hoverinfo='text',
        visible=True if i == 0 else False,  # Make the first plot visible
        #name=params['title'],
        name="Key",
        hoverlabel=dict(
            font_size=16,  # Increase the font size
            font_family="Arial",  # You can change the font as well
            bgcolor="red",  # Adjust background color of the hover box
            bordercolor="black",  # Adjust border color
        )
    ))

    # Add dropdown button for this dataset
    dropdown_buttons.append(dict(
        method="update",
        label=params['title'],
        args=[{"visible": [j == i for j in range(len(files_and_columns))] + [True] * 4},  # Ensure legend stays visible
              {"title": params['title'],
               "xaxis": {"title": params['fold_change_col']},
               "yaxis": {"title": f"-Log10({params['p_value_col']})"}}]  # Dynamically change the y-axis title
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

# Add a horizontal dashed line for the p-value threshold (-log10(0.05))
fig.add_shape(type="line", x0=-8, x1=8, y0=-np.log10(0.05), y1=-np.log10(0.05),
              line=dict(color="Black", dash="dash"))

# Extend vertical dashed lines for fold change thresholds over the entire plot range
fig.add_shape(type="line", x0=-0.5, x1=-0.5, y0=0, y1=1, yref="paper",
              line=dict(color="Black", dash="dash"))

fig.add_shape(type="line", x0=0.5, x1=0.5, y0=0, y1=1, yref="paper",
              line=dict(color="Black", dash="dash"))

# Set layout for the plot
fig.update_layout(
    title=files_and_columns[list(files_and_columns.keys())[0]]['title'],  # Set the initial title
    xaxis_title=files_and_columns[list(files_and_columns.keys())[0]]['fold_change_col'],  # Set the initial x-axis title
    yaxis_title=f"-Log10({files_and_columns[list(files_and_columns.keys())[0]]['p_value_col']})",  # Set initial y-axis title
    plot_bgcolor="lightslategray",
    paper_bgcolor="lightslategray",
    font=dict(color="black")
)

# Enable grid lines
fig.update_xaxes(showgrid=True)
fig.update_yaxes(showgrid=True)

# Save the plot as an HTML file
fig.write_html("volcano_plot.html")