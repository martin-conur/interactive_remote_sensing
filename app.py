# libraries needed
import numpy as np
import os
import json

import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import h5py
from dash.dependencies import State, Input, Output
from datetime import datetime, date, timedelta

# creating the server
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LITERA])
server = app.server
app.title = "Portal Imágenes Satelitales"

# extras
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}

# layout
app.layout = dbc.Container([
    html.H2("Portal Remote Sensing"),
    dcc.Store(id='local-data', storage_type='memory'),
    dbc.Row([
        dbc.Col(
            [
                html.H1(),
                html.H1(),
                html.Label("Fecha elegida:     "),
                dcc.DatePickerSingle(
                    id="date-picker",
                    min_date_allowed=date(2020, 10, 21),
                    max_date_allowed=date(2020, 10, 25),
                    initial_visible_month=datetime.now(),
                    date=datetime.today().date()-timedelta(1),
                    display_format="D MMM YYYY"
                ),
                html.H1(),
                html.Label("Producto: "),
                dcc.Dropdown(id="rs-dropdown",
                             options=[
                                {"label":"Clorofila a", "value":"chlor_a"},
                                {"label":"Temperatura Superficial", "value":"sst"}
                             ],
                             value="chlor_a"
                )
            ],xl=2,md=4
        ),
        dbc.Col(
            [
                dcc.Graph(id="map-graph")
            ], xl=5
        ),
        dbc.Col(
            [
                dcc.Graph(id="hist-graph"),
                dcc.Graph(id="line-graph")
            ], xl=5
        )
    ])
], fluid=True)

# @app.callback(Output("selected", "children"),
#               [Input("map-graph", "relayoutData")]
# )
# def display_selected_data(relayoutData):
#     sub_data = {"xaxis.range[0]":0,
#                 "xaxis.range[1]":200,
#                 "yaxis.range[0]":0,
#                 "yaxis.range[1]":200}
#     for key in relayoutData.keys():
#         sub_data[key] = relayoutData[key]
#     return json.dumps(sub_data, indent=2)
@app.callback(Output("line-graph", "figure"),
             [Input("map-graph", "relayoutData"),
              Input("rs-dropdown", "value")]
)
def line_graph_meker(relayoutData, product_value):

    path = os.path.join("data",product_value)
    files = os.listdir(path)
    #dates for plotting
    dates = [date(2020, 1, 1)+timedelta(int(f[:3])) for f in files]
    paths = [os.path.join(path, _) for _ in files]
    means = []
    for file in paths:
        file = h5py.File(file, "r")
        x = np.array(file["bands"][product_value])
        x[x == 0] = np.nan

        sub_data = {"xaxis.range[0]":0,
                    "xaxis.range[1]":x.shape[0],
                    "yaxis.range[0]":0,
                    "yaxis.range[1]":x.shape[1]}
        for key in relayoutData.keys():
            sub_data[key] = relayoutData[key]

        x_filtered = np.flip(x, axis=0)[int(sub_data["yaxis.range[0]"]):int(sub_data["yaxis.range[1]"]),
                                 int(sub_data["xaxis.range[0]"]):int(sub_data["xaxis.range[1]"])]
        x_filtered = x_filtered[~np.isnan(x_filtered)]
        means.append(np.mean(x_filtered))

    units = "°C" if product_value == "sst" else "ug/L"

    fig = go.Figure(data=go.Scatter(x=dates, y=means))
    fig.update_layout(
        title_text='Serie de tiempo {}'.format(product_value), # title of plot
        yaxis_title_text=f"{product_value} {units}", # yaxis label
        height=300,
        width=600,
        margin={"t":25,"b":0,"l":0,"r":0}
    )
    fig.update_yaxes(range=[0, 25])

    return fig
@app.callback(Output("hist-graph", "figure"),
              [Input("map-graph", "relayoutData"),
               Input("local-data", "data")]
)
def histogram_maker(relayoutData, data_dict):
    x = data_dict["data"] # reads the dict, I know, bad variables names

    sub_data = {"xaxis.range[0]":0,
                "xaxis.range[1]":np.array(x).shape[0],
                "yaxis.range[0]":0,
                "yaxis.range[1]":np.array(x).shape[1]}
    for key in relayoutData.keys():
        sub_data[key] = relayoutData[key]

    x_filtered = np.flip(np.array(x), axis=0)[int(sub_data["yaxis.range[0]"]):int(sub_data["yaxis.range[1]"]),
                             int(sub_data["xaxis.range[0]"]):int(sub_data["xaxis.range[1]"])]

    fig = go.Figure(data=[go.Histogram(x=x_filtered.flatten(), histnorm="percent", xbins=dict(
        start=-3.0,
        end=25))])
    fig.update_layout(
        title_text='Distribución {}'.format(data_dict["product"]), # title of plot
        xaxis_title_text=f"{data_dict['product']} {data_dict['units']}", # xaxis label
        yaxis_title_text='Porcentaje (%)', # yaxis label
        bargap=0.1, # gap between bars of adjacent location coordinates
        bargroupgap=0.1, # gap between bars of the same location coordinates
        height=300,
        width=600,
        margin={"t":25,"b":0,"l":0,"r":0}
    )

    return fig

@app.callback([Output("map-graph", "figure"),
               Output("local-data", "data")],
         [Input("date-picker", "date"),
          Input("rs-dropdown", "value")])
def product_updater(date_value, product_value):
    # day of the year
    doy = date.fromisoformat(date_value).timetuple().tm_yday
    path = os.path.join("data",product_value)
    path = os.path.join(path,  str(doy)+".h5")
    file = h5py.File(path, "r")
    data = np.array(file["bands"][product_value])
    land = np.array(file["bands"]["water_fraction"])
    data[data == 0] = np.nan

    # making the map
    # hiperparameters
    name = "°C" if product_value == "sst" else "ug/L"
    zmin = 6 if product_value == "sst" else 0
    zmax = 18 if product_value == "sst" else 40
    colorscale = "jet" if product_value == "sst" else [[0, "rgb(0, 0, 153)"],
                [1.0/100, "rgb(102, 255, 102)"],
                [1./30, "rgb(102, 255, 51)"],
                [1./10, "rgb(255, 255, 0)"],
                [1./2, "rgb(255, 153, 0)"],
                [1.0, "rgb(255, 51, 0)"]
    ]

    # the dict for storage
    data_dict = {}
    data_dict["data"] = list(data)
    data_dict["product"] = "Temperatura Superficial del Mar" if product_value == "sst" else "Clorofila a"
    data_dict["units"] = name

    fig = go.Figure(data = go.Heatmap(
                                z=np.flip(land, axis=0),
                                colorscale="gray", showscale=False, hoverinfo=None
                            ), layout=go.Layout(uirevision=True)
    )
    fig.add_trace(go.Heatmap(
            z=np.flip(data, axis=0),
            zmin=zmin,
            zmax=zmax,
            #colorscale=colorscale,
            text=np.round(np.flip(data, axis=0), 1),
            hoverinfo="text",
            hovertemplate = "TSM: %{text:.1f}" if product_value == "sst" else "chlor_a: %{text:.1f}",
            name=name,
            colorscale=colorscale
        )
    )
    fig.update_layout(height=600, width=600,
                      xaxis=dict(visible=False),
                      yaxis=dict(visible=False),
                      clickmode='event+select',
                      margin={"r":0, "l":0,"t":0, "b":0})
    return fig, data_dict



if __name__ == '__main__':
    app.run_server(debug=True)
