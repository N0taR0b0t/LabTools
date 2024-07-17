import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import pandas as pd

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define necessary columns
additional_columns = ['Calc. MW', 'm/z']
adj_p_columns = [
    'Adj. P-value: (cla) / (ctrl)',
    'Adj. P-value: (cla/lps) / (ctrl)',
    'Adj. P-value: (lps) / (ctrl)',
    'Adj. P-value: (no2-cla/lps) / (ctrl)'
]
p_columns = [
    'P-value: (cla) / (ctrl)',
    'P-value: (cla/lps) / (ctrl)',
    'P-value: (lps) / (ctrl)',
    'P-value: (no2-cla/lps) / (ctrl)'
]

# Load data from CSV and preprocess it
def load_and_preprocess_data(filepath):
    data = pd.read_csv(filepath, encoding='ISO-8859-1', on_bad_lines='skip')
    data.columns = data.columns.str.strip().str.replace('"', '')

    # Assign identifier based on the presence of Formula, Name, or Calc. MW
    def assign_identifier(row):
        if pd.notna(row['Formula']):
            return row['Formula']
        elif pd.notna(row['Name']):
            return row['Name']
        elif pd.notna(row['Calc. MW']):
            return str(row['Calc. MW'])
        else:
            return None

    data['Identifier'] = data.apply(assign_identifier, axis=1)
    
    # Ensure numeric conversion for p_value columns
    for col in additional_columns + p_columns + adj_p_columns:
        data[col] = pd.to_numeric(data[col], errors='coerce')

    # Round the additional columns to one decimal place
    for col in additional_columns:
        data[col] = data[col].round(1)

    # Special handling for the pathway with a semicolon in the name
    data['BioCyc Pathways'] = data['BioCyc Pathways'].fillna('')
    data['BioCyc Pathways'] = data['BioCyc Pathways'].str.replace(r'&gamma;-linolenate biosynthesis II \(animals\)', 'special_pathway')

    # Split and expand pathways into separate rows
    data = data.assign(**{
        'BioCyc Pathways': data['BioCyc Pathways'].str.split(';')
    }).explode('BioCyc Pathways')
    data['BioCyc Pathways'] = data['BioCyc Pathways'].str.strip()
    data['BioCyc Pathways'] = data['BioCyc Pathways'].str.replace('special_pathway', '&gamma;-linolenate biosynthesis II (animals)')

    return data

data = load_and_preprocess_data('AdjustedWorkflow.csv')

# Identify unique pathways
unique_pathways = data['BioCyc Pathways'].unique()
unique_pathways = [pathway for pathway in unique_pathways if pathway]  # Remove empty strings

# Function to format numeric values to scientific notation
def format_to_scientific(value):
    if pd.notna(value):
        try:
            return f"{float(value):.1e}"
        except ValueError:
            return value
    return value

# Function to check if a row has all red p-value cells
def has_all_red_cells(row):
    for adj_p_col in adj_p_columns:
        adj_p_value = pd.to_numeric(row[adj_p_col], errors='coerce')
        if pd.notna(adj_p_value) and adj_p_value < 0.05:
            return False
    return True

# Generate the tables for each pathway
def generate_tables_for_pathways(data, pathways, hide_red):
    tables = []
    for pathway in pathways:
        pathway_data = data[data['BioCyc Pathways'] == pathway]

        if hide_red:
            pathway_data = pathway_data[~pathway_data.apply(has_all_red_cells, axis=1)]

        pathway_data = pathway_data.sort_values(by='Calc. MW')

        # Generate the table columns
        columns = [
            {"name": "Identifier", "id": "Identifier"},
            {"name": "Calc. MW", "id": "Calc. MW"},
            {"name": "m/z", "id": "m/z"}
        ] + [{"name": col, "id": col} for col in adj_p_columns]

        # Apply scientific notation formatting to the adj_p_columns
        formatted_data = pathway_data.copy()
        for col in adj_p_columns:
            formatted_data[col] = formatted_data[col].apply(format_to_scientific)

        # Generate style conditions
        style_conditions = []
        for i, row in formatted_data.iterrows():
            for p_col, adj_p_col in zip(p_columns, adj_p_columns):
                try:
                    adj_p_value = float(row[adj_p_col])
                    p_value = float(row[p_col])
                    if pd.notna(adj_p_value) and adj_p_value < 0.05:
                        color = 'green'
                    elif pd.notna(p_value) and p_value < 0.05:
                        color = 'yellow'
                    else:
                        color = 'red'
                    text_color = 'white' if color in ['red', 'green'] else 'black'
                    style_conditions.append({
                        'if': {
                            'filter_query': f'{{Identifier}} = "{row["Identifier"]}" && {{{adj_p_col}}} = "{row[adj_p_col]}"',
                            'column_id': adj_p_col
                        },
                        'backgroundColor': color,
                        'color': text_color
                    })
                except (ValueError, TypeError):
                    continue

        # Create the table
        table = dash_table.DataTable(
            columns=columns,
            data=formatted_data.to_dict('records'),
            style_table={'overflowX': 'auto', 'minWidth': '100%'},
            style_cell={'textAlign': 'center', 'minWidth': '100px', 'maxWidth': '150px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=style_conditions,
            page_size=len(pathway_data)  # Display all rows on one page
        )
        tables.append(html.Div([
            html.H2(f'Pathway: {pathway}', className="text-center text-primary mb-4", style={"font-weight": "bold"}),
            table
        ]))
    return tables

# Layout of the app
app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                html.Button("Exclude insignificant rows", id="toggle-red-rows", className="btn btn-primary mb-4", style={"margin": "20px"}),
                width=12
            )
        ),
        dbc.Row(dbc.Col(html.H1("Significant Compound Pathway Tables", className="text-center text-primary mb-4", style={"font-weight": "bold"}), width=12)),
        html.Div(id='tables-container')
    ],
    fluid=True,
    style={"backgroundColor": "#f8f9fa", "padding": "20px"}
)

# Callback to update the table and button text
@app.callback(
    [Output("tables-container", "children"),
     Output("toggle-red-rows", "children")],
    [Input('toggle-red-rows', 'n_clicks')]
)
def update_tables(n_clicks):
    hide_red = (n_clicks is not None) and (n_clicks % 2 == 1)
    button_text = "Include insignificant rows" if hide_red else "Exclude insignificant rows"
    return generate_tables_for_pathways(data, unique_pathways, hide_red), button_text

if __name__ == '__main__':
    app.run_server(debug=True)