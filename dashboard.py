import sqlite3
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
from dash import Dash, dcc, html, callback, Input, Output, State, callback_context, ALL as all
import os
import base64
import io
import json
import numpy as np  # <--- HERE IS THE FIX

# ============================================================================
# CONFIGURATION
# ============================================================================
RESULTS_DIR = os.getenv('RESULTS_DIR', './waymo_dataset/results')
DB_PATH = os.path.join(RESULTS_DIR, 'edge_cases.db')

# ============================================================================
# DATABASE SETUP
# ============================================================================
if not os.path.exists(DB_PATH):
    print(f"✗ Database not found at {DB_PATH}")
    print(f"  Please run load_dataset.py first to populate the database")
    exit(1)

def get_edge_cases_data():
    """Load *PRE-FLAGGED* edge cases with full context from frames table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        # Join edge_cases with frames to get complete motion data and thumbnail
        query = '''
        SELECT 
            ec.id,
            ec.frame_id,
            ec.file_name,
            ec.timestamp,
            ec.edge_case_type,
            ec.severity,
            ec.reason,
            f.intent,
            f.speed_min,
            f.speed_max,
            f.speed_mean,
            f.accel_x_min,
            f.accel_x_max,
            f.accel_y_min,
            f.accel_y_max,
            f.jerk_x_max,
            f.jerk_y_max,
            f.panorama_thumbnail
        FROM edge_cases ec
        LEFT JOIN frames f ON ec.frame_id = f.frame_id
        ORDER BY ec.severity DESC
        '''
        df = pd.read_sql_query(query, conn)
        
        # Ensure panorama_thumbnail column exists (in case query returns empty or missing)
        if 'panorama_thumbnail' not in df.columns:
            df['panorama_thumbnail'] = None
        
        conn.close()
        return df
    except Exception as e:
        print(f"✗ Error loading database: {e}")
        exit(1)

# ============================================================================
# Ad-Hoc Query Configuration
# ============================================================================

# Define the ad-hoc queries your team wants to run
# These query the FULL 'frames' table, not just 'edge_cases'
AD_HOC_QUERIES = {
    'hard_brake_while_turning_right': {
        'name': 'Hard Brake while Turning Right',
        'query': """
            SELECT frame_id, file_name, intent, accel_x_min, speed_max
            FROM frames
            WHERE intent = 'GO_RIGHT' AND accel_x_min < -0.8
            ORDER BY accel_x_min ASC
            LIMIT 25
        """
    },
    'high_lateral_accel_going_straight': {
        'name': 'High Lateral Accel. while Going Straight (Suspicious)',
        'query': """
            SELECT frame_id, file_name, intent, accel_y_max, speed_max, accel_x_min
            FROM frames
            WHERE intent = 'GO_STRAIGHT' AND accel_y_max > 0.6
            ORDER BY accel_y_max DESC
            LIMIT 25
        """
    },
    'high_jerk_at_low_speed': {
        'name': 'High Jerk at Low Speed (Stop-Go Traffic?)',
        'query': """
            SELECT frame_id, file_name, intent, jerk_x_max, speed_max
            FROM frames
            WHERE speed_max < 5.0 AND jerk_x_max > 0.4
            ORDER BY jerk_x_max DESC
            LIMIT 25
        """
    }
}

def run_query(query_string):
    """General purpose function to run any query against the DB."""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(query_string, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"✗ Error running ad-hoc query: {e}")
        return pd.DataFrame() # Return empty dataframe on error

# ============================================================================
# Smart HTML Table Generator
# ============================================================================
def generate_html_table(df):
    """
    Converts a Pandas DataFrame to a Dash HTML Table.
    Automatically adds a 'Thumbnail' button if 'frame_id' column is present.
    """
    
    has_frame_id = 'frame_id' in df.columns
    
    # Build headers
    col_headers = []
    for col in df.columns:
        col_headers.append(html.Th(col, style={
            'padding': '10px',
            'textAlign': 'left',
            'borderBottom': '2px solid #ddd',
            'backgroundColor': '#f0f0f0',
            'fontWeight': 'bold',
            'fontSize': '11px',
            'whiteSpace': 'nowrap'
        }))
    if has_frame_id:
        col_headers.append(html.Th("Thumbnail", style={
            'padding': '10px',
            'textAlign': 'left',
            'borderBottom': '2px solid #ddd',
            'backgroundColor': '#f0f0f0',
            'fontWeight': 'bold',
            'fontSize': '11px'
        }))
    
    table_header = [html.Thead(html.Tr(col_headers))]
    
    # Build rows
    table_body_rows = []
    for i in range(len(df)):
        row_cells = []
        for col in df.columns:
            # Format cell content
            cell_content = str(df.iloc[i][col])
            # Apply rounding to numeric values for display
            if isinstance(df.iloc[i][col], (int, float, np.floating, np.integer)):
                 if abs(df.iloc[i][col]) > 0.001:
                    cell_content = f"{df.iloc[i][col]:.3f}"

            row_cells.append(
                html.Td(cell_content, style={
                    'padding': '8px',
                    'borderBottom': '1px solid #ddd',
                    'fontSize': '10px',
                    'maxWidth': '150px',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                    'whiteSpace': 'nowrap'
                })
            )
        
        # Add thumbnail button cell
        if has_frame_id:
            frame_id = int(df.iloc[i]['frame_id'])
            button_cell = html.Td(
                html.Button(
                    '📷 View',
                    id={'type': 'thumbnail-btn', 'index': frame_id},
                    n_clicks=0,
                    style={
                        'backgroundColor': '#4CAF50',
                        'color': 'white',
                        'border': 'none',
                        'padding': '6px 10px',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'fontSize': '11px',
                        'fontWeight': 'bold'
                    }
                ),
                style={
                    'padding': '8px',
                    'borderBottom': '1px solid #ddd',
                    'textAlign': 'center'
                }
            )
            row_cells.append(button_cell)
            
        table_body_rows.append(
            html.Tr(
                row_cells, 
                style={'backgroundColor': '#ffffff' if i % 2 == 0 else '#f9f9f9'}
            )
        )
    
    table_body = [html.Tbody(table_body_rows)]
    
    return html.Table(
        table_header + table_body, 
        style={
            'width': '100%',
            'borderCollapse': 'collapse',
            'marginTop': '10px',
            'fontSize': '11px'
        }
    )
# ============================================================================
# Load data once for the *main* dashboard
df = get_edge_cases_data()

if len(df) == 0:
    print("⚠ Database is empty - no *pre-flagged* edge cases found")
    # We don't exit here, as the ad-hoc queries might still work
    # exit(1) 

print(f"✓ Loaded {len(df)} *pre-flagged* edge cases from database")

# ============================================================================
# INITIALIZE DASH APP
# ============================================================================
app = Dash(__name__)

# ============================================================================
# APP LAYOUT
# ============================================================================
app.layout = html.Div([
    dcc.Store(id='current-page-store', data=1),  # Store current page number
    dcc.Store(id='thumbnail-modal-store', data={'frame_id': None, 'thumbnail_b64': None}),  # Store for thumbnail modal
    
    html.Div([
        html.H1("🚗 Waymo Edge Case Detection Dashboard", style={'textAlign': 'center', 'marginBottom': 30}),
    ], style={'backgroundColor': '#1f77b4', 'color': 'white', 'padding': '20px', 'borderRadius': '10px'}),
    
    # Thumbnail Modal
    html.Div([
        html.Div([
            html.Div([
                html.Button(
                    '✕ Close',
                    id='close-thumbnail-modal',
                    style={
                        'float': 'right',
                        'backgroundColor': '#d62728',
                        'color': 'white',
                        'border': 'none',
                        'padding': '8px 15px',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'fontWeight': 'bold'
                    }
                ),
                html.H2(id='thumbnail-modal-title', style={'margin': '0 0 15px 0'}),
            ], style={'marginBottom': '15px', 'overflow': 'auto'}),
            
            html.Img(
                id='thumbnail-modal-image',
                style={
                    'width': '100%',
                    'height': 'auto',
                    'maxHeight': '600px',
                    'borderRadius': '8px',
                    'marginBottom': '15px'
                }
            ),
            
            html.Div(id='thumbnail-modal-info', style={
                'backgroundColor': '#f9f9f9',
                'padding': '15px',
                'borderRadius': '8px',
                'fontSize': '13px'
            }),
        ], style={
            'backgroundColor': 'white',
            'padding': '25px',
            'borderRadius': '8px',
            'maxWidth': '900px',
            'margin': '50px auto',
            'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
        }),
    ], 
    id='thumbnail-modal',
    style={
        'display': 'none',
        'position': 'fixed',
        'zIndex': '1000',
        'left': '0',
        'top': '0',
        'width': '100%',
        'height': '100%',
        'backgroundColor': 'rgba(0,0,0,0.7)',
        'overflowY': 'auto'
    }),
    
    html.Div([
        # Summary Statistics Row
        html.Div([
            html.Div([
                html.H3(f"{len(df)}", style={'color': '#d62728', 'margin': 0}),
                html.P("Total Pre-Flagged Edge Cases", style={'margin': 0})
            ], style={
                'backgroundColor': '#f0f0f0',
                'padding': '20px',
                'borderRadius': '8px',
                'textAlign': 'center',
                'flex': 1,
                'margin': '10px'
            }),
            
            html.Div([
                html.H3(f"{df['file_name'].nunique()}", style={'color': '#2ca02c', 'margin': 0}),
                html.P("Files with Edge Cases", style={'margin': 0})
            ], style={
                'backgroundColor': '#f0f0f0',
                'padding': '20px',
                'borderRadius': '8px',
                'textAlign': 'center',
                'flex': 1,
                'margin': '10px'
            }),
            
            html.Div([
                html.H3(f"{df['edge_case_type'].nunique()}", style={'color': '#ff7f0e', 'margin': 0}),
                html.P("Edge Case Types", style={'margin': 0})
            ], style={
                'backgroundColor': '#f0f0f0',
                'padding': '20px',
                'borderRadius': '8px',
                'textAlign': 'center',
                'flex': 1,
                'margin': '10px'
            }),
            
            html.Div([
                # Handle empty df on load
                html.H3(f"{df['severity'].max():.2f}" if len(df) > 0 else "N/A", style={'color': '#9467bd', 'margin': 0}),
                html.P("Max Severity", style={'margin': 0})
            ], style={
                'backgroundColor': '#f0f0f0',
                'padding': '20px',
                'borderRadius': '8px',
                'textAlign': 'center',
                'flex': 1,
                'margin': '10px'
            }),
        ], style={'display': 'flex', 'justifyContent': 'space-around', 'marginBottom': '30px'}),
        
        # Filters Row
        html.Div([
            html.Div([
                html.Label("Filter by Edge Case Type:", style={'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='edge-case-filter',
                    options=[
                        {'label': 'All', 'value': 'all'},
                        *[{'label': f, 'value': f} for f in sorted(df['edge_case_type'].unique())]
                    ],
                    value='all',
                    style={'width': '100%'}
                ),
            ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '20px'}),
            
            html.Div([
                html.Label("Filter by File:", style={'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='file-filter',
                    options=[
                        {'label': 'All Files', 'value': 'all'},
                        *[{'label': f, 'value': f} for f in sorted(df['file_name'].unique())]
                    ],
                    value='all',
                    style={'width': '100%'}
                ),
            ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '20px'}),
            
            html.Div([
                html.Label("Severity Range:", style={'fontWeight': 'bold'}),
                dcc.RangeSlider(
                    id='severity-slider',
                    min=df['severity'].min() if len(df) > 0 else 0,
                    max=df['severity'].max() if len(df) > 0 else 1,
                    value=[df['severity'].min(), df['severity'].max()] if len(df) > 0 else [0,1],
                    marks={f'{v:.1f}': f'{v:.1f}' for v in [df['severity'].min(), df['severity'].max()]} if len(df) > 0 else {0:'0', 1:'1'},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], style={'width': '35%', 'display': 'inline-block'}),
        ], style={'marginBottom': '30px', 'padding': '20px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px'}),
        
        # Charts Row 1
        html.Div([
            html.Div([
                dcc.Graph(id='edge-case-distribution')
            ], style={'width': '48%', 'display': 'inline-block', 'marginRight': '2%'}),
            
            html.Div([
                dcc.Graph(id='severity-distribution')
            ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '2%'}),
        ]),
        
        # Charts Row 2
        html.Div([
            html.Div([
                dcc.Graph(id='severity-by-type')
            ], style={'width': '48%', 'display': 'inline-block', 'marginRight': '2%'}),
            
            html.Div([
                dcc.Graph(id='edge-cases-by-file')
            ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '2%'}),
        ]),
        
        # Charts Row 3 - Intent and Motion Metrics
        html.Div([
            html.Div([
                dcc.Graph(id='edge-cases-by-intent')
            ], style={'width': '48%', 'display': 'inline-block', 'marginRight': '2%'}),
            
            html.Div([
                dcc.Graph(id='motion-metrics-scatter')
            ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '2%'}),
        ]),

        # Ad-Hoc Query Section
        html.Div([
            html.H3("Ad-Hoc Query Analysis (Full Dataset)", style={'marginTop': '40px', 'marginBottom': '10px'}),
            html.P("Run specific queries against the complete 'frames' table, independent of the filters above."),
            
            dcc.Dropdown(
                id='ad-hoc-query-dropdown',
                options=[
                    {'label': v['name'], 'value': k} for k, v in AD_HOC_QUERIES.items()
                ],
                placeholder="Select a query to run...",
                style={'marginBottom': '20px'}
            ),
            
            dcc.Loading(
                id="loading-ad-hoc-query",
                type="default",
                children=html.Div(id='ad-hoc-query-output')
            )
        ], style={'marginBottom': '30px', 'padding': '20px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px'}),
        

        # Data Table with Pagination
        html.Div([
            html.H3("Pre-Flagged Edge Cases Details", style={'marginTop': '40px', 'marginBottom': '20px'}),
            
            # Pagination Controls
            html.Div(
                [
                    html.Button(
                        "← Previous",
                        id='prev-page-btn',
                        n_clicks=0,
                        style={
                            'margin': '5px',
                            'padding': '10px 15px',
                            'backgroundColor': '#636EFA',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '4px',
                            'cursor': 'pointer',
                            'fontWeight': 'bold'
                        }
                    ),
                    html.Span(
                        id='page-indicator',
                        style={
                            'margin': '0 20px',
                            'verticalAlign': 'middle',
                            'fontSize': '14px',
                            'fontWeight': 'bold'
                        }
                    ),
                    html.Button(
                        "Next →",
                        id='next-page-btn',
                        n_clicks=0,
                        style={
                            'margin': '5px',
                            'padding': '10px 15px',
                            'backgroundColor': '#636EFA',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '4px',
                            'cursor': 'pointer',
                            'fontWeight': 'bold'
                        }
                    ),
                ],
                style={'marginBottom': '15px', 'textAlign': 'center'}
            ),
            
            html.Div([
                html.Div(id='data-table'),
                html.Div(id='pagination-info', style={'marginTop': '15px', 'textAlign': 'center', 'fontWeight': 'bold'})
            ])
        ], style={'padding': '20px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px'}),
        
    ], style={'padding': '20px'})
], style={'fontFamily': 'Arial, sans-serif', 'backgroundColor': '#ffffff'})

# ============================================================================
# CALLBACKS
# ============================================================================

# Callback for Ad-Hoc Queries
@callback(
    Output('ad-hoc-query-output', 'children'),
    Input('ad-hoc-query-dropdown', 'value'),
    prevent_initial_call=True
)
def update_ad_hoc_query_output(query_key):
    if not query_key:
        return html.P("Please select a query to run.")
    
    # Get the query string from our config
    query_string = AD_HOC_QUERIES[query_key]['query']
    query_name = AD_HOC_QUERIES[query_key]['name']
    
    # Run the query
    results_df = run_query(query_string)
    
    if len(results_df) == 0:
        return html.Div([
            html.H5(f"Query: '{query_name}'"),
            html.P("Query ran successfully, but returned no results.", style={'fontWeight': 'bold'})
        ])
    
    # Format results as a table
    return html.Div([
        html.H5(f"Results for: '{query_name}'"),
        # Use the new smart table generator
        generate_html_table(results_df) 
    ])


# Thumbnail Modal Callback (Bug Fix)
@callback(
    [Output('thumbnail-modal', 'style'),
     Output('thumbnail-modal-image', 'src'),
     Output('thumbnail-modal-title', 'children'),
     Output('thumbnail-modal-info', 'children')],
    [Input({'type': 'thumbnail-btn', 'index': all}, 'n_clicks'),
     Input('close-thumbnail-modal', 'n_clicks')],
    prevent_initial_call=True
)
def display_thumbnail_modal(btn_clicks, close_clicks):
    """Display thumbnail modal when clicking on a frame row."""
    
    triggered_input = callback_context.triggered[0] if callback_context.triggered else None
    
    # If callback fired without user input (e.g., layout update) or 0 clicks, do nothing
    if not triggered_input or not triggered_input['value'] or triggered_input['value'] == 0:
         return {'display': 'none'}, '', '', ''
    
    triggered_prop_id = triggered_input['prop_id']
    
    # If close button was clicked, hide modal
    if 'close-thumbnail-modal' in triggered_prop_id:
        return {'display': 'none'}, '', '', ''
    
    # If a thumbnail button was clicked (and value is not 0 or None)
    if 'thumbnail-btn' in triggered_prop_id:
        try:
            # Extract frame_id from triggered button
            button_id = json.loads(triggered_prop_id.split('.')[0])
            frame_id = button_id['index']  # This is now frame_id
            
            # We must fetch this frame's data directly from the DB
            # to ensure we get data for *any* frame, not just pre-flagged ones.
            query = f"""
                SELECT 
                    f.*,
                    ec.edge_case_type,
                    ec.severity,
                    ec.reason
                FROM frames f
                LEFT JOIN edge_cases ec ON f.frame_id = ec.frame_id
                WHERE f.frame_id = ?
            """
            conn = sqlite3.connect(DB_PATH)
            frame_df = pd.read_sql_query(query, conn, params=(frame_id,))
            conn.close()
            
            if len(frame_df) == 0:
                print(f"No frame data found for frame_id {frame_id}")
                return {'display': 'none'}, '', '', ''
            
            frame_data = frame_df.iloc[0]
            
            # Get thumbnail
            thumbnail_bytes = frame_data['panorama_thumbnail']
            if thumbnail_bytes is None or pd.isna(thumbnail_bytes):
                print(f"No thumbnail bytes found for frame_id {frame_id}")
                return {'display': 'none'}, '', '', ''
            
            # Convert bytes to base64 image with proper JPEG header
            thumbnail_b64 = 'data:image/jpeg;base64,' + base64.b64encode(thumbnail_bytes).decode()
            
            # Check if it was a pre-flagged edge case
            edge_case_type = frame_data.get('edge_case_type', 'N/A')
            severity = frame_data.get('severity', 'N/A')
            reason = frame_data.get('reason', 'N/A')
            
            if pd.isna(edge_case_type) or edge_case_type is None:
                edge_case_type = 'N/A (Not Pre-Flagged)'
                severity = 'N/A'
                reason = 'N/A'
            
            # Format info
            info_html = html.Div([
                html.Div([
                    html.Span('Frame ID: ', style={'fontWeight': 'bold', 'color': '#1f77b4'}),
                    html.Span(f"{frame_data['frame_id']}")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Span('File: ', style={'fontWeight': 'bold', 'color': '#1f77b4'}),
                    html.Span(f"{frame_data['file_name']}")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Span('Edge Case: ', style={'fontWeight': 'bold', 'color': '#d62728'}),
                    html.Span(f"{edge_case_type}")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Span('Severity: ', style={'fontWeight': 'bold', 'color': '#d62728'}),
                    html.Span(f"{severity}" if isinstance(severity, str) else f"{severity:.3f}")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Span('Intent: ', style={'fontWeight': 'bold', 'color': '#1f77b4'}),
                    html.Span(f"{frame_data['intent']}")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Span('Speed: ', style={'fontWeight': 'bold', 'color': '#1f77b4'}),
                    html.Span(f"{frame_data['speed_min']:.2f} - {frame_data['speed_max']:.2f} m/s")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Span('Accel X: ', style={'fontWeight': 'bold', 'color': '#1f77b4'}),
                    html.Span(f"{frame_data['accel_x_min']:.3f} to {frame_data['accel_x_max']:.3f} m/s²")
                ], style={'marginBottom': '8px'}),
                html.Div([
                    html.Span('Reason: ', style={'fontWeight': 'bold', 'color': '#1f77b4'}),
                    html.Span(f"{reason}")
                ], style={'marginBottom': '0px'}),
            ])
            
            modal_style = {
                'display': 'block',
                'position': 'fixed',
                'zIndex': '1000',
                'left': '0',
                'top': '0',
                'width': '100%',
                'height': '100%',
                'backgroundColor': 'rgba(0,0,0,0.7)',
                'overflowY': 'auto'
            }
            
            modal_title = f"Frame {frame_data['frame_id']}"
            if edge_case_type != 'N/A (Not Pre-Flagged)':
                modal_title += f" - {edge_case_type}"

            return modal_style, thumbnail_b64, modal_title, info_html
        
        except Exception as e:
            print(f"Error displaying thumbnail: {e}")
            return {'display': 'none'}, '', '', f"Error: {str(e)}"
    
    # Default: hide modal
    return {'display': 'none'}, '', '', ''

# Main Dashboard Callback
@callback(
    [Output('edge-case-distribution', 'figure'),
     Output('severity-distribution', 'figure'),
     Output('severity-by-type', 'figure'),
     Output('edge-cases-by-file', 'figure'),
     Output('edge-cases-by-intent', 'figure'),
     Output('motion-metrics-scatter', 'figure'),
     Output('data-table', 'children'),
     Output('pagination-info', 'children'),
     Output('page-indicator', 'children'),
     Output('current-page-store', 'data')],
    [Input('edge-case-filter', 'value'),
     Input('file-filter', 'value'),
     Input('severity-slider', 'value'),
     Input('prev-page-btn', 'n_clicks'),
     Input('next-page-btn', 'n_clicks')],
    [State('current-page-store', 'data')]
)
def update_charts(edge_case_type, file_name, severity_range, prev_clicks, next_clicks, current_page):
    """Update all charts based on filters and pagination."""
    
    # Apply filters
    filtered_df = df.copy()
    
    # Handle case where df is empty
    if len(filtered_df) == 0:
        empty_fig = go.Figure()
        empty_fig.add_annotation(text="No data matches the selected filters", showarrow=False)
        empty_table = html.Div("No pre-flagged edge cases found", style={'textAlign': 'center', 'padding': '20px'})
        empty_pagination = html.Div("")
        empty_page_indicator = "Page 0 of 0"
        return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_table, empty_pagination, empty_page_indicator, 1

    if edge_case_type != 'all':
        filtered_df = filtered_df[filtered_df['edge_case_type'] == edge_case_type]
    
    if file_name != 'all':
        filtered_df = filtered_df[filtered_df['file_name'] == file_name]
    
    filtered_df = filtered_df[
        (filtered_df['severity'] >= severity_range[0]) & 
        (filtered_df['severity'] <= severity_range[1])
    ]
    
    # Handle empty filtered data
    if len(filtered_df) == 0:
        empty_fig = go.Figure()
        empty_fig.add_annotation(text="No data matches the selected filters", showarrow=False)
        empty_table = html.Div("No data matches the selected filters", style={'textAlign': 'center', 'padding': '20px'})
        empty_pagination = html.Div("")
        empty_page_indicator = "Page 0 of 0"
        return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_table, empty_pagination, empty_page_indicator, 1
    
    # Chart 1: Edge Case Distribution (Pie)
    edge_case_counts = filtered_df['edge_case_type'].value_counts()
    fig1 = px.pie(
        values=edge_case_counts.values,
        names=edge_case_counts.index,
        title='Distribution of Edge Case Types',
        color_discrete_sequence=px.colors.qualitative.Plotly
    )
    
    # Chart 2: Severity Distribution (Histogram)
    fig2 = px.histogram(
        filtered_df,
        x='severity',
        nbins=30,
        title='Severity Distribution',
        labels={'severity': 'Severity (m/s²)'},
        color_discrete_sequence=['#636EFA']
    )
    fig2.update_layout(showlegend=False)
    
    # Chart 3: Severity by Type (Box Plot)
    fig3 = px.box(
        filtered_df,
        x='edge_case_type',
        y='severity',
        title='Severity Range by Edge Case Type',
        labels={'severity': 'Severity (m/s²)', 'edge_case_type': 'Edge Case Type'},
        color='edge_case_type'
    )
    fig3.update_layout(showlegend=False)
    
    # Chart 4: Edge Cases by File (Bar)
    file_counts = filtered_df['file_name'].value_counts().head(10)
    fig4 = px.bar(
        x=file_counts.values,
        y=file_counts.index,
        orientation='h',
        title='Top 10 Files with Most Edge Cases',
        labels={'x': 'Count', 'y': 'File Name'},
        color_discrete_sequence=['#EF553B']
    )
    fig4.update_layout(showlegend=False)
    
    # Chart 5: Edge Cases by Intent (Bar)
    if 'intent' in filtered_df.columns and filtered_df['intent'].notna().any():
        intent_counts = filtered_df['intent'].value_counts().reset_index()
        intent_counts.columns = ['intent', 'count']
        fig5 = px.bar(
            intent_counts,
            x='intent',
            y='count',
            title='Edge Cases by Driving Intent',
            labels={'intent': 'Intent', 'count': 'Count'},
            color='intent',
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        fig5.update_layout(showlegend=False)
    else:
        fig5 = go.Figure()
        fig5.add_annotation(text="No intent data available", showarrow=False)
    
    # Chart 6: Motion Metrics Scatter (Speed vs Accel)
    if 'speed_max' in filtered_df.columns and 'accel_x_min' in filtered_df.columns:
        fig6 = px.scatter(
            filtered_df,
            x='speed_max',
            y='accel_x_min',
            color='edge_case_type',
            size='severity',
            hover_data=['frame_id', 'file_name', 'intent'],
            title='Speed vs Deceleration (bubble size = severity)',
            labels={'speed_max': 'Speed (m/s)', 'accel_x_min': 'Min Accel X (m/s²)'},
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
    else:
        fig6 = go.Figure()
        fig6.add_annotation(text="No motion data available", showarrow=False)
    
    # Data Table - with new motion metrics and pagination
    table_df = filtered_df[[
        'frame_id', 'file_name', 'intent', 'edge_case_type', 'severity', 'reason',
        'speed_min', 'speed_max', 'accel_x_min', 'accel_x_max', 'accel_y_min', 'accel_y_max', 
        'jerk_x_max', 'jerk_y_max'
    ]].copy()
    
    # Add a thumbnail column indicator for display (only if panorama_thumbnail exists)
    if 'panorama_thumbnail' in filtered_df.columns:
        table_df['thumbnail'] = filtered_df['panorama_thumbnail'].notna().apply(lambda x: '📷 View' if x else 'N/A')
    else:
        table_df['thumbnail'] = 'N/A'
    
    # Round numeric columns
    numeric_cols = ['severity', 'speed_min', 'speed_max', 'accel_x_min', 'accel_x_max', 
                    'accel_y_min', 'accel_y_max', 'jerk_x_max', 'jerk_y_max']
    for col in numeric_cols:
        if col in table_df.columns:
            table_df[col] = table_df[col].round(3)
    
    # Sort by severity descending
    table_df = table_df.sort_values('severity', ascending=False)
    
    # Pagination settings
    rows_per_page = 25
    total_rows = len(table_df)
    total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)
    
    # Update current page based on button clicks
    if prev_clicks or next_clicks:
        if prev_clicks and current_page > 1:
            current_page = current_page - 1
        elif next_clicks and current_page < total_pages:
            current_page = current_page + 1
    
    # Ensure current page is within bounds
    current_page = max(1, min(current_page, total_pages))
    
    # Calculate indices for current page
    start_idx = (current_page - 1) * rows_per_page
    end_idx = min(start_idx + rows_per_page, total_rows)
    page_df = table_df.iloc[start_idx:end_idx]
    
    # Build table rows with clickable thumbnail button
    table_rows = []
    for i in range(len(page_df)):
        row_cells = []
        for j, col in enumerate(page_df.columns):
            if col == 'thumbnail':
                # Make thumbnail cell clickable if it has data
                # Get the frame_id to find thumbnail in the original filtered_df
                frame_id = int(page_df.iloc[i]['frame_id'])  # Convert to Python int from numpy.int64
                thumbnail_exists = False
                
                # Search for this frame_id in filtered_df and check if it has a thumbnail
                matching_rows = filtered_df[filtered_df['frame_id'] == frame_id]
                if len(matching_rows) > 0 and 'panorama_thumbnail' in filtered_df.columns:
                    thumb_data = matching_rows.iloc[0]['panorama_thumbnail']
                    thumbnail_exists = thumb_data is not None and not pd.isna(thumb_data)
                
                if thumbnail_exists:
                    row_cells.append(
                        html.Td(
                            html.Button(
                                '📷 View',
                                id={'type': 'thumbnail-btn', 'index': frame_id},
                                n_clicks=0,
                                style={
                                    'backgroundColor': '#4CAF50',
                                    'color': 'white',
                                    'border': 'none',
                                    'padding': '6px 10px',
                                    'borderRadius': '4px',
                                    'cursor': 'pointer',
                                    'fontSize': '11px',
                                    'fontWeight': 'bold'
                                }
                            ),
                            style={
                                'padding': '8px',
                                'borderBottom': '1px solid #ddd',
                                'textAlign': 'center'
                            }
                        )
                    )
                else:
                    row_cells.append(
                        html.Td(
                            'N/A',
                            style={
                                'padding': '8px',
                                'borderBottom': '1px solid #ddd',
                                'fontSize': '10px',
                                'textAlign': 'center',
                                'color': '#999'
                            }
                        )
                    )
            else:
                row_cells.append(
                    html.Td(
                        str(page_df.iloc[i][col]),
                        style={
                            'padding': '8px',
                            'borderBottom': '1px solid #ddd',
                            'fontSize': '10px',
                            'maxWidth': '150px',
                            'overflow': 'hidden',
                            'textOverflow': 'ellipsis',
                            'whiteSpace': 'nowrap'
                        }
                    )
                )
        
        table_rows.append(
            html.Tr(
                row_cells,
                style={'backgroundColor': '#ffffff' if i % 2 == 0 else '#f9f9f9'}
            )
        )
    
    table_html = html.Div([
        # Table
        html.Table([
            html.Thead(
                html.Tr([
                    html.Th(col, style={
                        'padding': '10px',
                        'textAlign': 'left',
                        'borderBottom': '2px solid #ddd',
                        'backgroundColor': '#f0f0f0',
                        'fontWeight': 'bold',
                        'fontSize': '11px'
                    })
                    for col in page_df.columns
                ])
            ),
            html.Tbody(table_rows)
        ], style={
            'width': '100%',
            'borderCollapse': 'collapse',
            'marginTop': '10px',
            'fontSize': '11px'
        })
    ])
    
    # Pagination info text
    pagination_info = html.Div(
        f"Showing rows {start_idx + 1}-{end_idx} of {total_rows}",
        style={'color': '#666', 'fontSize': '13px'}
    )
    
    # Page indicator for the header
    page_indicator = f"Page {current_page} of {total_pages}"
    
    return fig1, fig2, fig3, fig4, fig5, fig6, table_html, pagination_info, page_indicator, current_page

# ============================================================================
# RUN SERVER
# ============================================================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Starting Waymo Edge Case Dashboard...")
    print("="*60)
    print(f"📊 Dashboard available at: http://localhost:8050")
    print(f"📁 Results directory: {RESULTS_DIR}")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=8050)
