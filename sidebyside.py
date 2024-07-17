import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import pandas as pd

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define necessary columns
ratio_columns = [
    'Ratio: (cla) / (ctrl)',
    'Ratio: (cla/lps) / (ctrl)',
    'Ratio: (lps) / (ctrl)',
    'Ratio: (no2-cla/lps) / (ctrl)'
]

p_columns = [
    'P-value: (cla) / (ctrl)',
    'P-value: (cla/lps) / (ctrl)',
    'P-value: (lps) / (ctrl)',
    'P-value: (no2-cla/lps) / (ctrl)'
]

adj_p_columns = [
    'Adj. P-value: (cla) / (ctrl)',
    'Adj. P-value: (cla/lps) / (ctrl)',
    'Adj. P-value: (lps) / (ctrl)',
    'Adj. P-value: (no2-cla/lps) / (ctrl)'
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
    data['Used Calc MW'] = data['Identifier'] == data['Calc. MW'].astype(str)
    
    # Ensure numeric conversion for ratio, p_value, and adj_p_value columns
    for col in ratio_columns + p_columns + adj_p_columns:
        data[col] = pd.to_numeric(data[col], errors='coerce')

    # Filter the data based on ratio conditions
    filtered_data = data[
        (data[ratio_columns[0]] < 0.8) | (data[ratio_columns[0]] > 1.25) |
        (data[ratio_columns[1]] < 0.8) | (data[ratio_columns[1]] > 1.25) |
        (data[ratio_columns[2]] < 0.8) | (data[ratio_columns[2]] > 1.25) |
        (data[ratio_columns[3]] < 0.8) | (data[ratio_columns[3]] > 1.25)
    ]

    # Exclude compounds with only red cells
    def has_non_red_cell(row):
        for p_col, adj_p_col in zip(p_columns, adj_p_columns):
            p_value = row[p_col]
            adj_p_value = row[adj_p_col]
            if (pd.notna(adj_p_value) and adj_p_value <= 0.05) or (pd.notna(p_value) and p_value <= 0.05):
                return True
        return False

    filtered_data = filtered_data[filtered_data.apply(has_non_red_cell, axis=1)]

    # Convert Identifier column to string to ensure consistent sorting
    filtered_data['Identifier'] = filtered_data['Identifier'].astype(str)

    # Sort the data alphabetically by Identifier, with those using Calc. MW at the bottom
    filtered_data = filtered_data.sort_values(by=['Used Calc MW', 'Identifier'])

    # Add a new display column combining p-value and adj p-value with spaces around '/'
    for p_col, adj_p_col in zip(p_columns, adj_p_columns):
        filtered_data[f'{p_col}_display'] = filtered_data.apply(lambda row: f"{row[p_col]:.1e} / {row[adj_p_col]:.1e}", axis=1)

    return filtered_data

data = load_and_preprocess_data('NicoleAll.csv')

# Define the color logic to be used in style_data_conditional
def generate_style_conditions(filtered_data):
    conditions = []
    for i, compound in filtered_data.iterrows():
        for p_col, adj_p_col in zip(p_columns, adj_p_columns):
            adj_p_value = pd.to_numeric(compound[adj_p_col], errors='coerce')
            p_value = pd.to_numeric(compound[p_col], errors='coerce')
            if pd.notna(adj_p_value) and adj_p_value <= 0.05:
                color = 'green'
            elif pd.notna(p_value) and p_value <= 0.05:
                color = 'yellow'
            else:
                color = 'red'
            conditions.append({
                'if': {
                    'filter_query': f'{{Identifier}} = "{compound["Identifier"]}" && {{{p_col}_display}} = "{compound[f"{p_col}_display"]}"',
                    'column_id': f'{p_col}_display'
                },
                'backgroundColor': color,
                'color': 'black' if color != 'red' else 'red'
            })
            if color == 'red':
                conditions[-1]['color'] = 'red'
                conditions[-1]['font'] = '0px'  # Hide text in red cells
    return conditions

# Layout of the app
app.layout = dbc.Container(
    [
        dbc.Row(dbc.Col(html.H1("Significant Compound Comparison", className="text-center text-primary mb-4", style={"font-weight": "bold"}), width=12)),
        dbc.Row(dbc.Col(dcc.Loading(id="loading", children=[html.Div(id="compounds-table")], type="default"), width=12))
    ],
    fluid=True,
    style={"backgroundColor": "#f8f9fa", "padding": "20px"}
)

# Callback to update the table
@app.callback(
    Output("compounds-table", "children"),
    Input('loading', 'children')  # Trigger when the app loads
)
def update_table(_):
    filtered_data = load_and_preprocess_data('NicoleAll.csv')
    display_columns = [f"{col}_display" for col in p_columns]
    return dash_table.DataTable(
        columns=[{"name": "Identifier", "id": "Identifier"}] + [{"name": col, "id": f"{col}_display"} for col in p_columns],
        data=filtered_data[['Identifier'] + display_columns].to_dict('records'),
        style_table={'overflowX': 'auto', 'minWidth': '100%'},
        style_cell={'textAlign': 'center', 'minWidth': '150px', 'maxWidth': '200px', 'whiteSpace': 'normal'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        style_data_conditional=generate_style_conditions(filtered_data),
        page_size=len(filtered_data)  # Display all rows on one page
    )

if __name__ == '__main__':
    app.run_server(debug=True)
