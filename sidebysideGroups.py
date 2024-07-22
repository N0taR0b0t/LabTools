import os
from flask import Flask, render_template, jsonify
import pandas as pd

app = Flask(__name__)

# Step 1: Identify and filter .txt files by their modification date
directory = '/Users/matias/Documents/GitHub/LabTools'
files = [f for f in os.listdir(directory) if f.endswith('.txt') and '(' in f and ')' in f]
files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)
selected_files = files[:4]

# Step 2: Parse the chemical formulas and categories from the files
def parse_file(file_path):
    with open(file_path, 'r') as file:
        data = file.read()
    categories = {}
    for line in data.split('\n'):
        if ':' in line:
            category, formulas = line.split(':')
            formulas = [formula.strip() for formula in formulas.split(',')]
            categories[category.strip()] = formulas
    return categories

file_data = {file: parse_file(os.path.join(directory, file)) for file in selected_files}

# Step 3: Get all unique formulas and compound groups
all_formulas = set()
compound_groups = set()
for categories in file_data.values():
    for group, formulas in categories.items():
        all_formulas.update(formulas)
        compound_groups.add(group)

formulas_list = sorted(all_formulas)
compound_groups = sorted(compound_groups)

# Step 4: Function to generate table data
def generate_table_data(selected_group):
    table_data = []
    for formula in formulas_list:
        row = []
        for file in selected_files:
            found = False
            if selected_group in file_data[file] and formula in file_data[file][selected_group]:
                found = True
            row.append(1 if found else 0)
        table_data.append(row)
    return table_data

@app.route('/')
def index():
    return render_template('index.html', files=selected_files, groups=compound_groups)

@app.route('/data/<group>')
def data(group):
    table_data = generate_table_data(group)
    return jsonify(table_data=table_data, formulas=formulas_list, files=selected_files)

if __name__ == '__main__':
    app.run(debug=True)