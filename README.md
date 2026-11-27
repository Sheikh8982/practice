# Excel Analysis Dashboard

A powerful Streamlit-based dashboard for drag-and-drop Excel file analysis with automatic data cleaning, profiling, and intelligent visualization.

## Features

- 📁 **Drag & Drop Upload** - Supports `.xlsx`, `.xls`, `.xlsm`, `.xlsb`, `.csv`
- 🔍 **Auto Data Profiling** - Column types, missing values, statistics, cardinality
- 🧹 **Auto Data Cleaning** - Type conversion, whitespace stripping, date parsing, empty row/col removal
- 📈 **Smart Visualizations** - Auto-detects best chart types:
  - Time series (line charts)
  - Categorical comparisons (bar charts)
  - Distributions (histograms, box plots)
  - Correlations (scatter plots, heatmaps)
  - Proportions (pie/donut charts)
- 🎨 **Multiple Color Themes** - Blue, Green, Sunset, Purple, Teal, Multi-color
- 💾 **Export Options** - Cleaned data (CSV/Excel) + Profile reports (JSON)

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Dashboard
```bash
streamlit run excel_dashboard.py
```

### 3. Open in Browser
The app will open at `http://localhost:8501`

## Usage

1. **Upload** - Drag an Excel/CSV file into the sidebar
2. **Select Sheet** - If multi-sheet Excel, choose from dropdown
3. **Analyze** - View auto-generated:
   - Data overview metrics
   - Column profile table
   - Data preview
   - Smart visualizations
   - Correlation matrix
4. **Export** - Download cleaned data or profile report

## Supported File Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| Excel (modern) | `.xlsx` | Full support, multi-sheet |
| Excel (legacy) | `.xls` | Via xlrd |
| Excel Macro | `.xlsm` | Read-only |
| Excel Binary | `.xlsb` | Requires pyxlsb |
| CSV | `.csv` | Auto-detects encoding |

## Color Themes

- **Default (Blue)** - Professional blue palette
- **Nature (Green)** - Green/teal tones
- **Sunset (Orange/Red)** - Warm colors
- **Purple** - Violet/purple palette
- **Ocean (Teal)** - Cyan/teal tones
- **Multi-color** - Distinct categorical colors

## Requirements

- Python 3.9+
- See `requirements.txt` for full list

## Project Structure

```
excel_dashboard.py    # Main Streamlit application
requirements.txt      # Python dependencies
```

## Customization

To customize the dashboard:
1. Modify `theme_colors` dict for custom palettes
2. Adjust `suggest_charts()` for different visualization logic
3. Edit `clean_dataframe()` for custom cleaning rules
4. Change chart styling in `create_chart()`

## License

MIT License - Feel free to use and modify.