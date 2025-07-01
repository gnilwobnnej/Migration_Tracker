import streamlit as st #build the webapp interface
import pandas as pd #handles the spreadsheets
import folium # draws interactive leaflet maps in python
from streamlit_folium import st_folium #embeds a folium map inside a streamlit page
from matplotlib import colormaps #gives nice reusable color palettes
import matplotlib.colors as mcolors #turns matplotlib colors into webfriendly strings.
import plotly.express as px #builds animated and interactive charts.
from pathlib import Path #makes file paths os independent. 



#tells streamlit to name the browser tab, "wide" lets the app stretch
st.set_page_config(page_title="Animal Migration Visualizer", layout="wide")

#adds a big headline at the top
st.title("Animal Migration Visualizer")

# --- Sidebar: data input
#picks the data source with a radio button.
data_source = st.sidebar.radio("Select data source:", ("Sample dataset", "Upload your own (.csv)"))

#Works out the path to a file called sample.csv sitting next to the Python script.
if data_source == "Sample dataset":
    sample_path = Path(__file__).with_name("sample.csv")
    #If the file isn’t there, show a red error and stop the program.
    if not sample_path.exists():
        st.error("Sample dataset not found. Please upload your own file named 'sample.csv' next to the app.")
        st.stop()
    #Reads the CSV into a Pandas DataFrame called df.
    df = pd.read_csv(sample_path)
else:
    #displays a file‑upload widget (only CSV is allowed).
    uploaded_file = st.sidebar.file_uploader("Upload CSV exported from Movebank", type="csv")
    if uploaded_file is None:
        st.info("Awaiting CSV upload.")
        st.stop()
    #if a file is not picked show a blue info box
    df = pd.read_csv(uploaded_file)

# Pre‑process 
#convers the timestamp column from plain text into read datetime objects, so we can group by time
df["timestamp"] = pd.to_datetime(df["timestamp"])

#sorts the table by the animal id and then time.
df = df.sort_values(["individual-local-identifier", "timestamp"])

#finds every unique animal ID in the dataset
animal_ids = df["individual-local-identifier"].unique()

#prints a bold animal count in the sidebar
st.sidebar.markdown(f"**Total animals:** {len(animal_ids)}")

#multi-select list - by default all animals are selected.
selected_animals = st.sidebar.multiselect("Select animal(s) to display:", animal_ids, default=list(animal_ids))

# Filter to selection
df = df[df["individual-local-identifier"].isin(selected_animals)]

# --- Main view selection 
#radio buttons in the main area toggle between the two maps.
view = st.radio("Choose view:", ("Static Map", "Animated Map"))

# --- Static Map 
if view == "Static Map":
    st.subheader("Static Migration Paths")

#a rough central point, zooms out a bit more if there is more than one animal. 
    center_lat = df["location-lat"].mean()
    center_lon = df["location-long"].mean()
    zoom_level = 6 if len(df) > 1 else 10

    #gives a satelite-style base layer "Esri worldImagery"
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_level, tiles="Esri WorldImagery")

    # Generate color palette (10 discrete)/ .resampled(N) stretches it so we get exactly N colors.
    # mcolors.to_hex converts them to #rrggbb strings for Folium.
    colors = colormaps["tab10"].resampled(len(animal_ids))
    color_map = {animal_id: mcolors.to_hex(colors(i)) for i, animal_id in enumerate(animal_ids)}

#for each selected animal extracts the coordinates
    for animal_id in selected_animals:
        animal_data = df[df["individual-local-identifier"] == animal_id]
        coords = animal_data[["location-lat", "location-long"]].values.tolist()

#add a colored polyline to the map
        folium.PolyLine(
            coords,
            color=color_map[animal_id],
            weight=3,
            opacity=0.8,
            tooltip=f"Animal {animal_id}",
        ).add_to(m)

        # Start / End markers
        folium.Marker(
            coords[0],
            icon=folium.Icon(color="green"),
            tooltip=f"Start – Animal {animal_id}\n{animal_data['timestamp'].iloc[0]}",
        ).add_to(m)
        folium.Marker(
            coords[-1],
            icon=folium.Icon(color="red"),
            tooltip=f"End – Animal {animal_id}\n{animal_data['timestamp'].iloc[-1]}",
        ).add_to(m)

#embeds the folium map in the page taking full width and 850px height
    st_folium(m, width="100%", height=850)

# --- Animated Map 
else:
    st.subheader("Animated Migration")

    # slider  chooses how many days of data appear in each animation frame.
    time_res = st.slider("Frame interval (days)", 1, 30, value=7)

#rouds each timestamp down to the nearest n day
    df["time_bin"] = df["timestamp"].dt.floor(f"{time_res}D")

#forces plotly to color by cat not numerical scale. 
    df["individual-local-identifier"] = df["individual-local-identifier"].astype(str)

    #each point rep an animal at one time slice. animation_frame sets the slider at the bottom of the chart. 
    fig = px.scatter_mapbox(
        df,
        lon="location-long",
        lat="location-lat",
        color="individual-local-identifier",
        animation_frame=df["time_bin"].dt.strftime("%Y-%m-%d"),
        animation_group="individual-local-identifier",
        hover_name="individual-local-identifier",
        zoom=5,
        height=850,
    )

    #chooses a light , minimal base map and enlarges the text and points. 
    fig.update_layout(
        mapbox_style="open-street-map",
        font=dict(size=14),
        legend=dict(
            title_font=dict(size=16),
            font=dict(size=14),
            itemsizing='constant'
    ),
        margin={"l": 0, "r": 0, "t": 10, "b": 10}
)
    fig.update_traces(marker=dict(size=10))

    #renters the interacting animation auto sizing to the page width. 
    st.plotly_chart(fig, use_container_width=True)
# --- Footer 

#adds the howto use section and keeps it hidden till clicked. 
with st.expander("How to use this app"):
    st.markdown(
        '''
        1. Upload own dataset or continue with the sample(Artic fox (Vulpes lagopus) from Argos Greenland (Karupelv)).    
        2. Filter the individual animal IDs if desired.  
        3. Switch between *Static Map* (folium) and *Animated Map* (Plotly) views.  
        4. Adjust the animation frame interval to smooth or accelerate the playback.  

        *Dependencies:* `streamlit`, `streamlit-folium`, `pandas`, `folium`, `plotly`, `matplotlib`.
        '''
    )