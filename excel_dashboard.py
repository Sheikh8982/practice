"""
Excel Analysis Dashboard - Streamlit App
Drag-and-drop Excel files for automatic analysis, cleaning, and visualization.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Excel Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e5e7eb;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1f2937;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #3b82f6;
    }
    .info-box {
        background: #eff6ff;
        border: 1px solid #3b82f6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stFileUploader > div > div > div > div {
        background: #f8fafc;
        border: 2px dashed #3b82f6;
        border-radius: 12px;
        padding: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def detect_column_type(series: pd.Series) -> str:
    """Detect the semantic type of a column."""
    if series.dtype in ['object', 'string']:
        # Check for datetime
        try:
            pd.to_datetime(series.dropna().iloc[0] if len(series.dropna()) > 0 else '')
            # If mostly parseable as dates
            parsed = pd.to_datetime(series, errors='coerce')
            if parsed.notna().sum() / len(series) > 0.7:
                return 'datetime'
        except:
            pass
        # Check for categorical (low cardinality)
        if series.nunique() / len(series) < 0.1 and series.nunique() < 20:
            return 'categorical'
        # Check for ID-like (high cardinality, unique)
        if series.nunique() == len(series):
            return 'identifier'
        return 'text'
    elif pd.api.types.is_numeric_dtype(series):
        if series.nunique() < 10 and series.min() >= 0:
            return 'discrete_numeric'
        return 'continuous_numeric'
    elif pd.api.types.is_datetime64_any_dtype(series):
        return 'datetime'
    return 'unknown'


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare dataframe for analysis."""
    df = df.copy()

    # Remove completely empty rows and columns
    df = df.dropna(how='all').dropna(axis=1, how='all')

    # Strip whitespace from string columns
    for col in df.select_dtypes(include=['object', 'string']).columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace('nan', np.nan)

    # Try to convert numeric columns stored as strings
    for col in df.select_dtypes(include=['object', 'string']).columns:
        # Try numeric conversion
        try:
            numeric = pd.to_numeric(df[col], errors='coerce')
            if numeric.notna().sum() / len(df[col]) > 0.8:
                df[col] = numeric
                continue
        except:
            pass

        # Try datetime conversion
        try:
            parsed = pd.to_datetime(df[col], errors='coerce', infer_datetime_format=True)
            if parsed.notna().sum() / len(df[col]) > 0.7:
                df[col] = parsed
                continue
        except:
            pass

    # Reset index
    df = df.reset_index(drop=True)

    return df


def generate_data_profile(df: pd.DataFrame) -> dict:
    """Generate comprehensive data profile."""
    profile = {
        'shape': df.shape,
        'columns': [],
        'memory_usage': df.memory_usage(deep=True).sum(),
        'duplicates': df.duplicated().sum(),
        'total_missing': df.isnull().sum().sum(),
    }

    for col in df.columns:
        col_info = {
            'name': col,
            'dtype': str(df[col].dtype),
            'type': detect_column_type(df[col]),
            'missing': df[col].isnull().sum(),
            'missing_pct': round(df[col].isnull().sum() / len(df) * 100, 2),
            'unique': df[col].nunique(),
            'unique_pct': round(df[col].nunique() / len(df) * 100, 2),
        }

        if col_info['type'] in ['continuous_numeric', 'discrete_numeric']:
            col_info.update({
                'min': df[col].min(),
                'max': df[col].max(),
                'mean': df[col].mean(),
                'median': df[col].median(),
                'std': df[col].std(),
                'q25': df[col].quantile(0.25),
                'q75': df[col].quantile(0.75),
            })
        elif col_info['type'] == 'categorical':
            col_info['top_values'] = df[col].value_counts().head(10).to_dict()
        elif col_info['type'] == 'datetime':
            col_info.update({
                'min': df[col].min(),
                'max': df[col].max(),
                'range_days': (df[col].max() - df[col].min()).days if pd.notna(df[col].max()) and pd.notna(df[col].min()) else None,
            })

        profile['columns'].append(col_info)

    return profile


def suggest_charts(profile: dict) -> list:
    """Suggest appropriate chart types based on data profile."""
    suggestions = []
    cols = profile['columns']

    numeric_cols = [c for c in cols if c['type'] in ['continuous_numeric', 'discrete_numeric']]
    categorical_cols = [c for c in cols if c['type'] == 'categorical']
    datetime_cols = [c for c in cols if c['type'] == 'datetime']
    text_cols = [c for c in cols if c['type'] == 'text']

    # Time series
    if datetime_cols and numeric_cols:
        for dt_col in datetime_cols[:2]:
            for num_col in numeric_cols[:3]:
                suggestions.append({
                    'type': 'line',
                    'title': f'{num_col["name"]} over {dt_col["name"]}',
                    'x': dt_col['name'],
                    'y': num_col['name'],
                    'priority': 'high'
                })

    # Bar charts: categorical vs numeric
    if categorical_cols and numeric_cols:
        for cat_col in categorical_cols[:3]:
            for num_col in numeric_cols[:3]:
                suggestions.append({
                    'type': 'bar',
                    'title': f'{num_col["name"]} by {cat_col["name"]}',
                    'x': cat_col['name'],
                    'y': num_col['name'],
                    'priority': 'high'
                })

    # Scatter: numeric vs numeric
    if len(numeric_cols) >= 2:
        for i, x_col in enumerate(numeric_cols[:3]):
            for y_col in numeric_cols[i+1:4]:
                suggestions.append({
                    'type': 'scatter',
                    'title': f'{y_col["name"]} vs {x_col["name"]}',
                    'x': x_col['name'],
                    'y': y_col['name'],
                    'priority': 'medium'
                })

    # Histogram for numeric
    for num_col in numeric_cols[:4]:
        suggestions.append({
            'type': 'histogram',
            'title': f'Distribution of {num_col["name"]}',
            'x': num_col['name'],
            'priority': 'medium'
        })

    # Pie/Donut for categorical
    for cat_col in categorical_cols[:3]:
        if cat_col['unique'] <= 15:
            suggestions.append({
                'type': 'pie',
                'title': f'Distribution of {cat_col["name"]}',
                'values': cat_col['name'],
                'priority': 'medium'
            })

    # Box plot for numeric by categorical
    if categorical_cols and numeric_cols:
        for cat_col in categorical_cols[:2]:
            for num_col in numeric_cols[:3]:
                suggestions.append({
                    'type': 'box',
                    'title': f'{num_col["name"]} by {cat_col["name"]}',
                    'x': cat_col['name'],
                    'y': num_col['name'],
                    'priority': 'low'
                })

    # Correlation heatmap
    if len(numeric_cols) >= 3:
        suggestions.append({
            'type': 'heatmap',
            'title': 'Correlation Matrix',
            'priority': 'high'
        })

    return suggestions


def create_chart(df: pd.DataFrame, suggestion: dict, color_palette: list = None):
    """Create a Plotly chart based on suggestion."""
    if color_palette is None:
        color_palette = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

    chart_type = suggestion['type']
    title = suggestion['title']

    try:
        if chart_type == 'line':
            fig = px.line(df, x=suggestion['x'], y=suggestion['y'], title=title,
                         color_discrete_sequence=color_palette)
            fig.update_traces(line=dict(width=2.5))

        elif chart_type == 'bar':
            # Aggregate if needed
            if df[suggestion['x']].nunique() > 30:
                top_cats = df[suggestion['x']].value_counts().head(20).index
                plot_df = df[df[suggestion['x']].isin(top_cats)]
            else:
                plot_df = df

            agg_df = plot_df.groupby(suggestion['x'])[suggestion['y']].mean().reset_index()
            agg_df = agg_df.sort_values(suggestion['y'], ascending=True)

            fig = px.bar(agg_df, x=suggestion['y'], y=suggestion['x'], orientation='h',
                        title=title, color_discrete_sequence=color_palette)

        elif chart_type == 'scatter':
            fig = px.scatter(df, x=suggestion['x'], y=suggestion['y'], title=title,
                           color_discrete_sequence=color_palette, opacity=0.6,
                           trendline='ols' if len(df) < 5000 else None)

        elif chart_type == 'histogram':
            fig = px.histogram(df, x=suggestion['x'], title=title,
                             color_discrete_sequence=color_palette, nbins=30,
                             marginal='box')

        elif chart_type == 'pie':
            value_counts = df[suggestion['values']].value_counts().head(15)
            fig = px.pie(values=value_counts.values, names=value_counts.index,
                        title=title, color_discrete_sequence=color_palette,
                        hole=0.4)

        elif chart_type == 'box':
            fig = px.box(df, x=suggestion['x'], y=suggestion['y'], title=title,
                        color_discrete_sequence=color_palette)

        elif chart_type == 'heatmap':
            numeric_df = df.select_dtypes(include=[np.number])
            if len(numeric_df.columns) >= 2:
                corr = numeric_df.corr()
                fig = px.imshow(corr, title=title, color_continuous_scale='RdBu_r',
                               zmin=-1, zmax=1, aspect='auto',
                               text_auto='.2f')
                fig.update_layout(height=500)
            else:
                return None

        else:
            return None

        # Common layout updates
        fig.update_layout(
            title_font_size=14,
            title_font_color='#1f2937',
            font_family='Inter, system-ui, sans-serif',
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=60, r=40, t=60, b=60),
            hoverlabel=dict(bgcolor='white', font_size=12),
            xaxis=dict(showgrid=True, gridcolor='#f3f4f6', gridwidth=1),
            yaxis=dict(showgrid=True, gridcolor='#f3f4f6', gridwidth=1),
        )

        return fig

    except Exception as e:
        st.warning(f"Could not create chart '{title}': {str(e)}")
        return None


# ============================================================
# MAIN APP
# ============================================================

def main():
    # Header
    st.markdown('<h1 class="main-header">📊 Excel Analysis Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload Excel files for automatic cleaning, profiling, and intelligent visualization</p>', unsafe_allow_html=True)

    # Sidebar - File Upload
    with st.sidebar:
        st.markdown("### 📁 Upload Excel File")
        uploaded_file = st.file_uploader(
            "Drag and drop or click to browse",
            type=['xlsx', 'xls', 'xlsm', 'xlsb', 'csv'],
            help="Supports .xlsx, .xls, .xlsm, .xlsb, .csv files"
        )

        if uploaded_file:
            st.success(f"✅ Loaded: {uploaded_file.name}")
            st.info(f"Size: {uploaded_file.size / 1024:.1f} KB")

        st.markdown("---")
        st.markdown("### ⚙️ Settings")

        # Sheet selection (for Excel files with multiple sheets)
        if uploaded_file and uploaded_file.name.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb')):
            # We'll read sheet names after loading
            pass

        # Analysis options
        st.checkbox("Auto-clean data", value=True, key="auto_clean")
        st.checkbox("Show data profile", value=True, key="show_profile")
        st.checkbox("Auto-generate charts", value=True, key="auto_charts")
        st.checkbox("Show correlation matrix", value=True, key="show_corr")

        st.markdown("---")
        st.markdown("### 🎨 Color Theme")
        theme = st.selectbox(
            "Chart color palette",
            ["Default (Blue)", "Nature (Green)", "Sunset (Orange/Red)", "Purple", "Ocean (Teal)", "Multi-color"],
            index=0
        )

        theme_colors = {
            "Default (Blue)": ['#3b82f6', '#1e40af', '#60a5fa', '#93c5fd', '#dbeafe'],
            "Nature (Green)": ['#10b981', '#059669', '#34d399', '#6ee7b7', '#d1fae5'],
            "Sunset (Orange/Red)": ['#f59e0b', '#d97706', '#fbbf24', '#fcd34d', '#fef3c7'],
            "Purple": ['#8b5cf6', '#7c3aed', '#a78bfa', '#c4b5fd', '#ede9fe'],
            "Ocean (Teal)": ['#06b6d4', '#0891b2', '#22d3ee', '#67e8f9', '#cffafe'],
            "Multi-color": ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'],
        }

    # Main content area
    if uploaded_file is None:
        # Landing state
        st.markdown("""
        <div class="info-box">
            <h3>🚀 Getting Started</h3>
            <ol>
                <li><strong>Drag & drop</strong> an Excel file (.xlsx, .xls, .csv) into the sidebar</li>
                <li>The dashboard will <strong>automatically analyze</strong> your data</li>
                <li>View <strong>data quality report</strong>, <strong>smart visualizations</strong>, and <strong>key insights</strong></li>
                <li><strong>Export</strong> cleaned data or chart images</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

        # Features preview
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            #### 🔍 Auto Analysis
            - Data type detection
            - Missing value analysis
            - Duplicate detection
            - Statistical summaries
            """)
        with col2:
            st.markdown("""
            #### 📈 Smart Charts
            - Time series detection
            - Categorical comparisons
            - Distribution analysis
            - Correlation matrices
            """)
        with col3:
            st.markdown("""
            #### 🧹 Data Cleaning
            - Auto type conversion
            - Whitespace stripping
            - Empty row/col removal
            - Date parsing
            """)
        return

    # Load and process file
    with st.spinner("🔄 Loading and analyzing file..."):
        try:
            # Read file based on extension
            if uploaded_file.name.endswith('.csv'):
                # Try different encodings
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        uploaded_file.seek(0)
                        raw_df = pd.read_csv(uploaded_file, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raw_df = pd.read_csv(uploaded_file, encoding='utf-8', errors='ignore')
            else:
                # Excel file - get sheet names first
                uploaded_file.seek(0)
                xls = pd.ExcelFile(uploaded_file)

                if len(xls.sheet_names) > 1:
                    sheet_name = st.sidebar.selectbox("Select Sheet", xls.sheet_names)
                else:
                    sheet_name = xls.sheet_names[0]

                uploaded_file.seek(0)
                raw_df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

            # Clean data
            if st.session_state.get('auto_clean', True):
                df = clean_dataframe(raw_df)
            else:
                df = raw_df.copy()

            # Generate profile
            profile = generate_data_profile(df)

        except Exception as e:
            st.error(f"❌ Error loading file: {str(e)}")
            return

    # ============================================================
    # DATA OVERVIEW METRICS
    # ============================================================
    st.markdown('<h2 class="section-header">📋 Data Overview</h2>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Rows", f"{profile['shape'][0]:,}", help="Total number of records")
    with col2:
        st.metric("Columns", f"{profile['shape'][1]:,}", help="Total number of fields")
    with col3:
        st.metric("Missing Values", f"{profile['total_missing']:,}",
                 delta=f"{profile['total_missing']/profile['shape'][0]/profile['shape'][1]*100:.1f}%" if profile['shape'][0] > 0 else "0%")
    with col4:
        st.metric("Duplicates", f"{profile['duplicates']:,}",
                 delta=f"{profile['duplicates']/profile['shape'][0]*100:.1f}%" if profile['shape'][0] > 0 else "0%")
    with col5:
        mem_mb = profile['memory_usage'] / 1024 / 1024
        st.metric("Memory", f"{mem_mb:.1f} MB")

    # ============================================================
    # DATA PROFILE TABLE
    # ============================================================
    if st.session_state.get('show_profile', True):
        st.markdown('<h2 class="section-header">🔍 Column Profile</h2>', unsafe_allow_html=True)

        profile_df = pd.DataFrame([{
            'Column': c['name'],
            'Type': c['type'].replace('_', ' ').title(),
            'Dtype': c['dtype'],
            'Missing': f"{c['missing']:,} ({c['missing_pct']}%)",
            'Unique': f"{c['unique']:,} ({c['unique_pct']}%)",
            'Sample Values': str(list(c.get('top_values', {}).keys())[:3]) if c['type'] == 'categorical' else
                           f"{c.get('min', 'N/A')} – {c.get('max', 'N/A')}" if c['type'] in ['continuous_numeric', 'discrete_numeric'] else 'N/A'
        } for c in profile['columns']])

        st.dataframe(profile_df, use_container_width=True, hide_index=True)

    # ============================================================
    # DATA PREVIEW
    # ============================================================
    st.markdown('<h2 class="section-header">👀 Data Preview</h2>', unsafe_allow_html=True)

    preview_cols = st.columns([3, 1])
    with preview_cols[1]:
        n_rows = st.selectbox("Rows to show", [10, 25, 50, 100, "All"], index=1)

    if n_rows == "All":
        st.dataframe(df, use_container_width=True, height=400)
    else:
        st.dataframe(df.head(n_rows), use_container_width=True, height=400)

    # ============================================================
    # SMART VISUALIZATIONS
    # ============================================================
    if st.session_state.get('auto_charts', True):
        st.markdown('<h2 class="section-header">📈 Auto-Generated Visualizations</h2>', unsafe_allow_html=True)

        suggestions = suggest_charts(profile)
        color_palette = theme_colors.get(theme, theme_colors["Multi-color"])

        if not suggestions:
            st.info("No chart suggestions available for this dataset. Try adding more varied data types.")
        else:
            # Priority ordering
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            suggestions.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 2))

            # Display charts in a grid
            high_priority = [s for s in suggestions if s.get('priority') == 'high']
            other_priority = [s for s in suggestions if s.get('priority') != 'high']

            # High priority charts - full width or 2-col
            if high_priority:
                st.markdown("#### 🎯 Key Insights")
                for i, suggestion in enumerate(high_priority[:4]):
                    fig = create_chart(df, suggestion, color_palette)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, key=f"chart_high_{i}")

            # Other charts in expandable sections
            if other_priority:
                with st.expander("📊 Additional Charts", expanded=False):
                    for i, suggestion in enumerate(other_priority[:8]):
                        fig = create_chart(df, suggestion, color_palette)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True, key=f"chart_other_{i}")

    # ============================================================
    # CORRELATION MATRIX
    # ============================================================
    if st.session_state.get('show_corr', True):
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) >= 2:
            st.markdown('<h2 class="section-header">🔗 Correlation Analysis</h2>', unsafe_allow_html=True)

            corr = numeric_df.corr()

            # Heatmap
            fig = px.imshow(
                corr,
                title="Correlation Matrix",
                color_continuous_scale='RdBu_r',
                zmin=-1, zmax=1,
                text_auto='.2f',
                aspect='auto'
            )
            fig.update_layout(
                height=500,
                font_family='Inter, system-ui, sans-serif',
                title_font_size=14
            )
            st.plotly_chart(fig, use_container_width=True)

            # Strong correlations table
            strong_corr = []
            for i in range(len(corr.columns)):
                for j in range(i+1, len(corr.columns)):
                    val = corr.iloc[i, j]
                    if abs(val) > 0.5:
                        strong_corr.append({
                            'Variable 1': corr.columns[i],
                            'Variable 2': corr.columns[j],
                            'Correlation': round(val, 3),
                            'Strength': 'Strong' if abs(val) > 0.7 else 'Moderate'
                        })

            if strong_corr:
                st.markdown("#### 🎯 Notable Correlations")
                st.dataframe(pd.DataFrame(strong_corr), use_container_width=True, hide_index=True)

    # ============================================================
    # EXPORT SECTION
    # ============================================================
    st.markdown('<h2 class="section-header">💾 Export</h2>', unsafe_allow_html=True)

    export_cols = st.columns(3)

    with export_cols[0]:
        # Download cleaned data as CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Cleaned Data (CSV)",
            csv,
            file_name=f"cleaned_{uploaded_file.name.split('.')[0]}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with export_cols[1]:
        # Download cleaned data as Excel
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Data')
            # Add profile sheet
            profile_df.to_excel(writer, index=False, sheet_name='Data Profile')
        excel_buffer.seek(0)
        st.download_button(
            "📥 Download Cleaned Data (Excel)",
            excel_buffer,
            file_name=f"cleaned_{uploaded_file.name.split('.')[0]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with export_cols[2]:
        # Download profile report as JSON
        import json
        profile_json = json.dumps(profile, indent=2, default=str)
        st.download_button(
            "📥 Download Profile Report (JSON)",
            profile_json,
            file_name=f"profile_{uploaded_file.name.split('.')[0]}.json",
            mime="application/json",
            use_container_width=True
        )


if __name__ == "__main__":
    main()