# import packages
import pandas as pd
import numpy as np
import geopandas as gpd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import dash, dcc, html, callback_context
from dash.dependencies import Input, Output, State

# import api keys
import config

# define external stylesheet
external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

# downlaod data and perform transformations for each dataset
# parks
parks_url = "https://data.cityofnewyork.us/api/geospatial/enfh-gkve?method=export&format=Shapefile"
gdf_parks = gpd.read_file(parks_url)
gdf_parks.to_crs(4326, inplace=True)

# cdta
cdta_url = "https://data.cityofnewyork.us/api/geospatial/xn3r-zk6y?accessType=DOWNLOAD&method=export&format=Shapefile"
gdf_cdta = gpd.read_file(cdta_url)
gdf_cdta.to_crs(4326, inplace=True)
# add acre column in gdf_cd
gdf_cdta["cdta_acres"] = round(gdf_cdta["shape_area"] / 43560)

# parks cdta
# join parks with cdta to get hoverData column in parks dataset
gdf_parks_cdta = gpd.sjoin(gdf_parks, gdf_cdta)


# create map plot
# define trace for parks layer
trace_parks = go.Choroplethmapbox(
    geojson=gdf_parks_cdta.geometry.__geo_interface__,
    locations=gdf_parks_cdta.index,
    z=[1] * len(gdf_parks_cdta),
    hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}",
    customdata=gdf_parks_cdta[["cdtaname", "eapply"]],
    colorscale=[[0, "rgb(1,68,34)"], [1, "rgb(1,68,34)"]],  # single color for all
    marker_opacity=0.75,
    marker_line_width=0,
    showscale=False,
    name="Parks",
    visible=True,
)


# define trace for cdta layer
trace_comm_districts = go.Choroplethmapbox(
    geojson=gdf_cdta.geometry.__geo_interface__,
    locations=gdf_cdta.index,
    z=gdf_cdta["cdta_acres"],
    hovertemplate="<b>%{customdata[0]}</b><br><br>"
    + "CDTA Acres: %{z:,}<br>"
    + "<extra></extra>",
    customdata=gdf_cdta[["cdtaname", "cdta_acres"]],
    colorscale="Blues",
    marker_opacity=0.5,
    marker_line_width=2,
    marker_line_color="gray",
    name="Community Districts",
    visible=True,
)

# define map layout
layout = go.Layout(
    mapbox_style="mapbox://styles/mapbox/light-v10",
    mapbox_zoom=9,
    mapbox_center={"lat": 40.7, "lon": -73.9},
    mapbox_accesstoken=config.MAPBOX_API,
    margin={"l": 0, "r": 0, "t": 30, "b": 0},
    updatemenus=[
        dict(
            type="buttons",
            direction="left",
            buttons=list(
                [
                    dict(
                        label="Parks",
                        method="update",
                        args=[{"visible": [True, False]}],
                    ),
                    dict(
                        label="Community District Tabulation Areas",
                        method="update",
                        args=[{"visible": [False, True]}],
                    ),
                    dict(
                        label="Both",
                        method="update",
                        args=[{"visible": [True, True]}],
                    ),
                ]
            ),
            showactive=True,
            pad={"r": 10, "t": 10},
            x=0.75,
            xanchor="right",
            y=0,
            yanchor="bottom",
        )
    ],
)

# create map with subplots
map = make_subplots(rows=1, cols=1, specs=[[{"type": "mapbox"}]])

# add traces to map
map.add_trace(trace_parks)
map.add_trace(trace_comm_districts)

# update map layour
map.update_layout(layout)

# acs
acs_2021_url = "https://s-media.nyc.gov/agencies/dcp/assets/files/excel/data-tools/census/acs/demo_2021acs5yr_cdta.xlsx"
df_acs_cdta_2021 = pd.read_excel(acs_2021_url)
# replace different name for QN14
df_acs_cdta_2021["GeogName"] = df_acs_cdta_2021["GeogName"].replace(
    ["QN14 The Rockaways (CD 14 Equivalent)"],
    "QN14 The Rockaways (CD 14 Approximation)",
)

# join cdta and parks for indicator
# perform the spatial join
gdf_cdta_parks = gpd.sjoin(gdf_cdta, gdf_parks, predicate="intersects")
# sum up the park acres for each CDTA
df_cdta_parks_sum = (
    gdf_cdta_parks.groupby("cdta2020")
    .agg({"cdtaname": "first", "acres": "sum", "cdta_acres": "first"})
    .reset_index()
)

# create the Dash app
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# create a list of cdta for the dropdown menu
cdta_list = df_cdta_parks_sum["cdtaname"].unique()
cdta_options = [{"label": cdta, "value": cdta} for cdta in cdta_list]

# define the app layout
app.layout = html.Div(
    [
        html.H1(
            "NYC Parks and Racial Distribution",
            style={"text-align": "center"},
        ),
        html.H3(id="cdta-subtitle", style={"text-align": "center"}),
        html.Div(
            [
                dcc.Markdown(
                    """
        #### Instructions:
        Select Community District Tabulation Area (CDTA) by hovering over map area, or select from drop-down.
        """
                ),
                dcc.Graph(
                    id="nyc-cdta-park-map",
                    figure=map,
                    hoverData={
                        "points": [
                            {
                                "customdata": [
                                    "BK01 Williamsburg-Greenpoint (CD 1 Equivalent)",
                                    0,
                                ]
                            }
                        ]
                    },
                ),
                html.Br(),
                dcc.Markdown(
                    """
        ##### Select CDTA:
        """
                ),
                dcc.Dropdown(
                    id="cdta-dropdown",
                    options=cdta_options,
                    value=cdta_options[0]["value"],
                    multi=False,
                ),
                html.Br(),
                dcc.Markdown(
                    """
        **Data Sources:**

        [NYC Open Data - Parks Properties](https://data.cityofnewyork.us/Recreation/Parks-Properties/enfh-gkve)

        [NYC Open Data 2020 Community District Tabulation Areas (CDTAs)](https://data.cityofnewyork.us/City-Government/2020-Community-District-Tabulation-Areas-CDTAs-Tab/xn3r-zk6y)

        [NYC Population Fact Finder](https://popfactfinder.planning.nyc.gov/#11.67/40.7198/-73.9515)
        """,
                    link_target="_blank",
                ),
            ],
            style={
                "width": "50%",
                "float": "left",
                "display": "inline-block",
                "padding": "0 20",
                "height": {"size": "95vh"},
            },
        ),
        html.Div(
            [
                dcc.Graph(id="race-graph", style={"height": "400px"}),
                dcc.Graph(id="indicator-graph", style={"height": "400px"}),
            ],
            style={
                "display": "inline-block",
                "float": "right",
                "width": "50%",
                "height": {"size": "95vh"},
            },
        ),
    ]
)


@app.callback(
    Output("cdta-subtitle", "children"),
    Input("nyc-cdta-park-map", "hoverData"),
    Input("cdta-dropdown", "value"),
)
def update_subtitle(hoverData, dropdown_value):
    triggered_input = callback_context.triggered[0]["prop_id"].split(".")[0]
    if triggered_input == "nyc-cdta-park-map":
        cdta_name = hoverData["points"][0]["customdata"][0]
        return f"{cdta_name}"
    else:
        return f"{dropdown_value}"


# create race graph
def create_race_graph(df_filtered):
    # Select columns for bar graph
    race_columns = ["WtNHP", "BlNHP", "AsnNHP", "Hsp1P", "OthNHP", "Rc2plNHP"]
    race_labels = [
        "White",
        "Black or African American",
        "Asian",
        "Hispanic or Latino",
        "Some Other Race",
        "Two or More Races",
    ]
    # Create bar graph
    fig = go.Figure(
        go.Bar(
            x=race_labels,
            y=df_filtered[race_columns].values[0],  # Select first row of data
            marker_color=[
                "#636EFA",
                "#EF553B",
                "#00CC96",
                "#AB63FA",
                "#FFA15A",
                "#19D3F3",
            ],  # Set bar colors
        )
    )

    # Add title and axes labels
    fig.update_layout(
        title={
            "text": "Racial Distribution",
            "y": 0.9,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top",
            "font": {
                "size": 18,
            },
        },
        xaxis_title="",
        yaxis_title="Percentage of Total Population",
    )

    return fig


# define the callback function for the race graph
@app.callback(
    Output("race-graph", "figure"),
    Input("nyc-cdta-park-map", "hoverData"),
    Input("cdta-dropdown", "value"),
)
def update_race_graph(hoverData, dropdown_value):
    triggered_input = callback_context.triggered[0]["prop_id"].split(".")[0]
    if triggered_input == "nyc-cdta-park-map":
        cdta_name = hoverData["points"][0]["customdata"][0]
        df_filtered = df_acs_cdta_2021[df_acs_cdta_2021["GeogName"] == cdta_name]
        return create_race_graph(df_filtered)
    else:
        df_filtered = df_acs_cdta_2021[df_acs_cdta_2021["GeogName"] == dropdown_value]
        return create_race_graph(df_filtered)


# create indicator graph
def create_indicator_graph(
    acres,
    Q1,
    Q3,
    outlier_low,
    outlier_high,
    median_acreage,
    min_range,
    max_range,
):
    # Create a gauge indicator
    indicator = go.Indicator(
        mode="gauge+number",
        value=acres,
        title={"text": "Park Acreage", "font": {"size": 18}},
        gauge={
            "axis": {
                "range": [
                    min_range,
                    max_range,
                ]
            },
            "steps": [
                {"range": [0, Q1], "color": "lightgray"},
                {"range": [Q1, Q3], "color": "gray"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": median_acreage,
            },
        },
    )

    # Add a label for the median
    if indicator.value > median_acreage and indicator.value < outlier_high:
        label = go.layout.Annotation(
            text="Above Median",
            align="center",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )
    elif indicator.value > outlier_high:
        label = go.layout.Annotation(
            text="Outlier High",
            align="center",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )

    elif indicator.value < outlier_low:
        label = go.layout.Annotation(
            text="Outlier Low",
            align="center",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )
    elif indicator.value < median_acreage and indicator.value > outlier_low:
        label = go.layout.Annotation(
            text="Below Median",
            align="center",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )

    else:
        pass

    fig = go.Figure(indicator, layout=go.Layout(annotations=[label]))

    return fig


# define callback for indicator
@app.callback(
    Output("indicator-graph", "figure"),
    Input("nyc-cdta-park-map", "hoverData"),
    Input("cdta-dropdown", "value"),
)
def update_indicator(hoverData, dropdown_value):
    # get stats
    min_range = min(df_cdta_parks_sum["acres"])
    max_range = max(df_cdta_parks_sum["acres"])
    Q1 = np.percentile(df_cdta_parks_sum["acres"], 25)
    Q3 = np.percentile(df_cdta_parks_sum["acres"], 75)
    IQR = Q3 - Q1
    outlier_low = Q1 - (IQR * 1.5)
    outlier_high = Q3 + (IQR * 1.5)
    median_acreage = np.median(df_cdta_parks_sum["acres"])

    # filter the data based on selected cdta
    triggered_input = callback_context.triggered[0]["prop_id"].split(".")[0]
    if triggered_input == "nyc-cdta-park-map":
        cdta_name = hoverData["points"][0]["customdata"][0]
        df_2_filtered = df_cdta_parks_sum[df_cdta_parks_sum["cdtaname"] == cdta_name]
        acres = int(round(df_2_filtered["acres"]))
        return create_indicator_graph(
            acres,
            Q1,
            Q3,
            outlier_low,
            outlier_high,
            median_acreage,
            min_range,
            max_range,
        )
    else:
        df_2_filtered = df_cdta_parks_sum[
            df_cdta_parks_sum["cdtaname"] == dropdown_value
        ]
        acres = int(round(df_2_filtered["acres"]))
        return create_indicator_graph(
            acres,
            Q1,
            Q3,
            outlier_low,
            outlier_high,
            median_acreage,
            min_range,
            max_range,
        )


# run the app
if __name__ == "__main__":
    app.run_server(debug=True)
