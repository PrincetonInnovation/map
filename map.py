from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import pydeck as pdk
import streamlit as st

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Princeton Region Innovation Resources",
    page_icon="👨‍🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Keep this filename exactly as currently configured.
DATA_FILE = Path("Princeton-Innovation-Assets_WIP.csv")

# Public, token-free CARTO basemap.
CARTO_POSITRON_STYLE = (
    "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
)

# Princeton / Office of Innovation-inspired palette.
PRINCETON_ORANGE = "#EE7F2D"
PRINCETON_ORANGE_DARK = "#C95B12"
PRINCETON_ORANGE_LIGHT = "#FFF0E6"
SIDEBAR_DARK_GRAY = "#343434"
SIDEBAR_DARKER_GRAY = "#262626"
INK = "#1D1D1B"
DARK_GRAY = "#3E3E3E"
MEDIUM_GRAY = "#666666"
LIGHT_GRAY = "#E6E6E6"
OFF_WHITE = "#FCFCFB"
WHITE = "#FFFFFF"

# Map-marker colors are RGB lists for PyDeck.
DEFAULT_MARKER_COLOR = [100, 100, 100]

CATEGORY_COLORS = {
    "Coworking": [0, 119, 139],
    "Wet/Dry Lab": [91, 135, 74],
    "Prototyping": [126, 84, 164],
    "Prototyping (Accelerator-members Only)": [238, 127, 45],
    "Coworking (Accelerator-members Only)": [238, 127, 45],
    "Research Core Facility": [238, 127, 45],
}

REQUIRED_COLUMNS = [
    "Category",
    "Organization Name",
    "Address",
    "Distance from Princeton U (mi)",
    "Space Type",
    "Published Price",
    "Princeton Affiliation Discount?",
    "More Info / Website",
    "Accelerator / Incubator Program & NJEDA Recognition",
    "Latitude",
    "Longitude",
]


# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------


def inject_innovation_theme() -> None:
    """Apply a Princeton-inspired interface theme."""
    st.markdown(
        f"""
        <style>
            :root {{
                --princeton-orange: {PRINCETON_ORANGE};
                --princeton-orange-dark: {PRINCETON_ORANGE_DARK};
                --princeton-orange-light: {PRINCETON_ORANGE_LIGHT};
                --sidebar-dark-gray: {SIDEBAR_DARK_GRAY};
                --sidebar-darker-gray: {SIDEBAR_DARKER_GRAY};
                --ink: {INK};
                --dark-gray: {DARK_GRAY};
                --medium-gray: {MEDIUM_GRAY};
                --light-gray: {LIGHT_GRAY};
                --off-white: {OFF_WHITE};
                --white: {WHITE};
            }}

            .stApp,
            [data-testid="stAppViewContainer"] {{
                background-color: var(--off-white);
                color: var(--ink);
            }}

            [data-testid="stHeader"] {{
                background: rgba(252, 252, 251, 0.95);
            }}

            /* Left filter panel */
            [data-testid="stSidebar"] {{
                background-color: var(--sidebar-dark-gray);
                border-right: 1px solid var(--sidebar-darker-gray);
            }}

            [data-testid="stSidebar"] * {{
                color: var(--white);
            }}

            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3 {{
                color: var(--white);
            }}

            [data-testid="stSidebar"] [data-baseweb="select"] > div {{
                background-color: var(--white);
                border-color: var(--white);
            }}

            [data-testid="stSidebar"] [data-baseweb="select"] input,
            [data-testid="stSidebar"] [data-baseweb="select"] span {{
                color: var(--ink) !important;
            }}

            [data-testid="stSidebar"] .stTextInput input {{
                background-color: var(--white);
                color: var(--ink) !important;
                border-color: var(--white);
            }}

            /* Selected Multiselect category tags */
            [data-testid="stSidebar"] [data-baseweb="tag"] {{
                background-color: var(--princeton-orange) !important;
                border-color: var(--princeton-orange) !important;
            }}

            [data-testid="stSidebar"] [data-baseweb="tag"] span,
            [data-testid="stSidebar"] [data-baseweb="tag"] div,
            [data-testid="stSidebar"] [data-baseweb="tag"] svg {{
                color: var(--ink) !important;
                fill: var(--ink) !important;
            }}

            /* Sidebar sliders and checkboxes */
            [data-testid="stSidebar"] [data-baseweb="slider"]
            div[role="slider"] {{
                background-color: var(--princeton-orange) !important;
            }}

            [data-testid="stSidebar"] [data-baseweb="slider"]
            div[role="progressbar"] {{
                background-color: var(--princeton-orange) !important;
            }}

            [data-testid="stSidebar"] input[type="checkbox"]:checked {{
                accent-color: var(--princeton-orange);
            }}

            h1 {{
                color: var(--ink);
                font-weight: 700;
                letter-spacing: -0.02em;
            }}

            h2, h3 {{
                color: var(--ink);
                font-weight: 650;
            }}

            p, li {{
                color: var(--dark-gray);
            }}

            [data-testid="stMetric"] {{
                background: var(--white);
                border: 1px solid var(--light-gray);
                border-top: 4px solid var(--princeton-orange);
                border-radius: 3px;
                padding: 0.8rem 1rem;
            }}

            [data-testid="stMetricLabel"] {{
                color: var(--medium-gray);
                font-weight: 600;
            }}

            [data-testid="stMetricValue"] {{
                color: var(--ink);
            }}

            button[kind="primary"],
            button[kind="secondary"] {{
                background-color: var(--princeton-orange) !important;
                border: 1px solid var(--princeton-orange) !important;
                color: var(--ink) !important;
                font-weight: 700 !important;
            }}

            button[kind="primary"] *,
            button[kind="secondary"] * {{
                color: var(--ink) !important;
                -webkit-text-fill-color: var(--ink) !important;
                opacity: 1 !important;
            }}

            button[kind="primary"]:hover,
            button[kind="secondary"]:hover {{
                background-color: var(--princeton-orange-dark) !important;
                border-color: var(--princeton-orange-dark) !important;
                color: var(--white) !important;
            }}

            button[kind="primary"]:hover *,
            button[kind="secondary"]:hover * {{
                color: var(--white) !important;
                -webkit-text-fill-color: var(--white) !important;
            }}

            button[kind="primary"]:focus,
            button[kind="secondary"]:focus {{
                outline: 3px solid var(--princeton-orange-light) !important;
                outline-offset: 2px !important;
            }}

            /*
            Resource detail actions use ordinary HTML anchors rather than
            st.link_button(), ensuring visible text in every Streamlit version.
            */
            .resource-action-button {{
                display: block;
                width: 100%;
                box-sizing: border-box;
                margin: 0.75rem 0;
                padding: 0.8rem 1rem;
                background-color: var(--princeton-orange) !important;
                border: 1px solid var(--princeton-orange) !important;
                border-radius: 0.5rem;
                color: var(--ink) !important;
                -webkit-text-fill-color: var(--ink) !important;
                text-align: center;
                text-decoration: none !important;
                font-weight: 700 !important;
                opacity: 1 !important;
            }}

            .resource-action-button:hover,
            .resource-action-button:focus {{
                background-color: var(--princeton-orange-dark) !important;
                border-color: var(--princeton-orange-dark) !important;
                color: var(--white) !important;
                -webkit-text-fill-color: var(--white) !important;
                text-decoration: none !important;
            }}

            .resource-action-button:focus {{
                outline: 3px solid var(--princeton-orange-light);
                outline-offset: 2px;
            }}

            /* Explicit tab styling keeps inactive labels visible. */
            .stTabs [data-baseweb="tab-list"] {{
                gap: 1.5rem;
                border-bottom: 1px solid var(--light-gray);
            }}

            .stTabs button[role="tab"],
            .stTabs button[role="tab"] > *,
            .stTabs button[role="tab"] > * > *,
            .stTabs button[role="tab"] span,
            .stTabs button[role="tab"] p,
            .stTabs [data-baseweb="tab"],
            .stTabs [data-baseweb="tab"] > *,
            .stTabs [data-baseweb="tab"] > * > *,
            .stTabs [data-baseweb="tab"] span,
            .stTabs [data-baseweb="tab"] p {{
                color: var(--dark-gray) !important;
                -webkit-text-fill-color: var(--dark-gray) !important;
                opacity: 1 !important;
                font-weight: 650 !important;
            }}

            .stTabs button[role="tab"] {{
                background-color: transparent !important;
                padding: 0.55rem 0.05rem 0.65rem 0.05rem;
            }}

            .stTabs button[role="tab"]:hover,
            .stTabs button[role="tab"]:hover > *,
            .stTabs button[role="tab"]:hover > * > *,
            .stTabs button[role="tab"]:hover span,
            .stTabs button[role="tab"]:hover p,
            .stTabs [data-baseweb="tab"]:hover,
            .stTabs [data-baseweb="tab"]:hover > *,
            .stTabs [data-baseweb="tab"]:hover > * > *,
            .stTabs [data-baseweb="tab"]:hover span,
            .stTabs [data-baseweb="tab"]:hover p {{
                color: var(--princeton-orange-dark) !important;
                -webkit-text-fill-color: var(
                    --princeton-orange-dark
                ) !important;
            }}

            .stTabs button[role="tab"][aria-selected="true"],
            .stTabs button[role="tab"][aria-selected="true"] > *,
            .stTabs button[role="tab"][aria-selected="true"] > * > *,
            .stTabs button[role="tab"][aria-selected="true"] span,
            .stTabs button[role="tab"][aria-selected="true"] p,
            .stTabs [data-baseweb="tab"][aria-selected="true"],
            .stTabs [data-baseweb="tab"][aria-selected="true"] > *,
            .stTabs [data-baseweb="tab"][aria-selected="true"] > * > *,
            .stTabs [data-baseweb="tab"][aria-selected="true"] span,
            .stTabs [data-baseweb="tab"][aria-selected="true"] p {{
                color: var(--princeton-orange-dark) !important;
                -webkit-text-fill-color: var(
                    --princeton-orange-dark
                ) !important;
                font-weight: 750 !important;
            }}

            .stTabs [data-baseweb="tab-highlight"] {{
                background-color: var(--princeton-orange) !important;
            }}

            a {{
                color: var(--princeton-orange-dark);
                font-weight: 600;
            }}

            a:hover {{
                color: var(--ink);
            }}

            [data-testid="stDataFrame"] {{
                background: var(--white);
                border: 1px solid var(--light-gray);
                border-radius: 3px;
            }}

            [data-testid="stExpander"] {{
                background: var(--white);
                border: 1px solid var(--light-gray);
                border-radius: 3px;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_innovation_theme()


# -----------------------------------------------------------------------------
# Data helpers
# -----------------------------------------------------------------------------


def clean_text(value: object) -> str:
    """Return a clean string, including for blank and missing cells."""
    if pd.isna(value):
        return ""

    return " ".join(str(value).replace("\xa0", " ").split())


def extract_first_url(value: object) -> str:
    """Return the first usable URL in a potentially mixed-text cell."""
    text = clean_text(value)

    match = re.search(
        r"(https?://[^\s,;]+|www\.[^\s,;]+)",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    url = match.group(1).rstrip(".,);]}>")

    if url.lower().startswith("www."):
        url = f"https://{url}"

    return url


def extract_distance(value: object) -> float | None:
    """Extract a numerical distance from a source cell."""
    match = re.search(r"\d+(?:\.\d+)?", clean_text(value))
    return float(match.group()) if match else None


def classify_affiliation(note: object) -> str:
    """Turn detailed affiliation notes into concise dashboard filter values."""
    text = clean_text(note).lower()

    if not text or "needs outreach" in text:
        return "Needs outreach"

    if any(term in text for term in ["yes", "potential", "princeton faculty"]):
        return "Potential / confirmed"

    if any(term in text for term in ["n/a", "not applicable"]):
        return "Not applicable"

    return "Unclear"


def classify_program_status(note: object) -> str:
    """Turn detailed program notes into concise dashboard filter values."""
    text = clean_text(note).lower()

    if not text:
        return "No information"

    if "nj ignite-approved" in text or "nj ignite approved" in text:
        return "NJ Ignite approved"

    if "strategic innovation center" in text:
        return "Strategic Innovation Center"

    if any(term in text for term in ["accelerator", "incubator", "cohort"]):
        return "Accelerator / incubator"

    if any(
        term in text
        for term in [
            "no accelerator",
            "not found on",
            "no formal accelerator",
            "no formal incubator",
        ]
    ):
        return "No formal program"

    return "Other / needs review"


def category_color(category: object) -> list[int]:
    """Map each resource category to its marker RGB color."""
    return CATEGORY_COLORS.get(
        clean_text(category),
        DEFAULT_MARKER_COLOR,
    )


def google_maps_url(address: object) -> str:
    """Create a direct address-search link for Google Maps."""
    return (
        "https://www.google.com/maps/search/?api=1&query="
        f"{quote(clean_text(address))}"
    )


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------


@st.cache_data
def load_assets(csv_path: str) -> pd.DataFrame:
    """
    Load the coordinate-enabled asset CSV.

    Try UTF-8 first, then Windows-1252 for CSVs saved by Excel or containing
    Windows smart punctuation such as curly apostrophes and quotation marks.
    """
    read_options = {
        "dtype": str,
        "keep_default_na": False,
    }

    try:
        df = pd.read_csv(
            csv_path,
            encoding="utf-8-sig",
            **read_options,
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            csv_path,
            encoding="cp1252",
            **read_options,
        )

    df.columns = [clean_text(column) for column in df.columns]

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    for column in df.columns:
        df[column] = df[column].map(clean_text)

    df = df[
        df["Organization Name"].ne("")
        & ~df["Organization Name"].str.contains(
            "organization name",
            case=False,
            na=False,
        )
    ].copy()

    df["Latitude"] = pd.to_numeric(
        df["Latitude"],
        errors="coerce",
    )

    df["Longitude"] = pd.to_numeric(
        df["Longitude"],
        errors="coerce",
    )

    df["Distance (mi)"] = df[
        "Distance from Princeton U (mi)"
    ].map(extract_distance)

    df["Website URL"] = df["More Info / Website"].map(extract_first_url)

    df["Affiliation Status"] = df[
        "Princeton Affiliation Discount?"
    ].map(classify_affiliation)

    df["Program Status"] = df[
        "Accelerator / Incubator Program & NJEDA Recognition"
    ].map(classify_program_status)

    searchable_columns = [
        "Category",
        "Organization Name",
        "Address",
        "Space Type",
        "Published Price",
        "Princeton Affiliation Discount?",
        "Accelerator / Incubator Program & NJEDA Recognition",
    ]

    df["Search Text"] = (
        df[searchable_columns]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .str.lower()
    )

    return df.sort_values(
        by=["Distance (mi)", "Organization Name"],
        na_position="last",
    ).reset_index(drop=True)


# -----------------------------------------------------------------------------
# Map rendering
# -----------------------------------------------------------------------------


def render_map(filtered_assets: pd.DataFrame) -> None:
    """Render a CARTO basemap with category-colored resource markers."""
    mapped = filtered_assets.dropna(
        subset=["Latitude", "Longitude"]
    ).copy()

    if mapped.empty:
        st.warning(
            "No mapped records match the current filters. Check that the "
            "CSV contains numeric Latitude and Longitude values."
        )
        return

    mapped["marker_color"] = mapped["Category"].apply(category_color)
    mapped["maps_url"] = mapped["Address"].apply(google_maps_url)

    mapped["distance_display"] = mapped["Distance (mi)"].apply(
        lambda value: (
            f"{value:.1f} miles"
            if pd.notna(value)
            else "Not listed"
        )
    )

    center_latitude = mapped["Latitude"].mean()
    center_longitude = mapped["Longitude"].mean()

    if len(mapped) == 1:
        zoom = 12
    elif len(mapped) <= 5:
        zoom = 10
    else:
        zoom = 9

    marker_layer = pdk.Layer(
        "ScatterplotLayer",
        data=mapped,
        get_position="[Longitude, Latitude]",
        get_fill_color="marker_color",
        get_radius=280,
        radius_min_pixels=8,
        radius_max_pixels=24,
        pickable=True,
        stroked=True,
        get_line_color=[255, 255, 255],
        line_width_min_pixels=1,
    )

    tooltip = {
        "html": """
        <b>{Organization Name}</b><br/>
        <b>Category:</b> {Category}<br/>
        <b>Address:</b> {Address}<br/>
        <b>Distance:</b> {distance_display}<br/>
        <b>Program status:</b> {Program Status}<br/><br/>
        <a href="{maps_url}" target="_blank">Open in Google Maps</a>
        """,
        "style": {
            "backgroundColor": "#FFFFFF",
            "color": "#1D1D1B",
            "fontSize": "13px",
            "padding": "10px",
        },
    }

    deck = pdk.Deck(
        layers=[marker_layer],
        initial_view_state=pdk.ViewState(
            latitude=center_latitude,
            longitude=center_longitude,
            zoom=zoom,
            pitch=0,
        ),
        map_provider="carto",
        map_style=CARTO_POSITRON_STYLE,
        tooltip=tooltip,
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
        height=650,
    )


# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------


if not DATA_FILE.exists():
    st.error(
        f"Could not find `{DATA_FILE.name}`. Keep `map.py` and the "
        "coordinate-enabled CSV in the same directory."
    )
    st.stop()

try:
    assets = load_assets(str(DATA_FILE))
except Exception as exc:
    st.error("The CSV could not be loaded.")
    st.exception(exc)
    st.stop()

st.title("Princeton Region Innovation Resources")
st.caption(
    "Coworking, laboratory, prototyping, shared research-core, accelerator, "
    "and incubator resources in the Princeton-area innovation ecosystem."
)

# Sidebar filters
st.sidebar.header("Directory filters")

categories = sorted(assets["Category"].dropna().unique().tolist())

selected_categories = st.sidebar.multiselect(
    "Space category",
    options=categories,
    default=categories,
)

valid_distances = assets["Distance (mi)"].dropna()

maximum_distance = (
    float(valid_distances.max())
    if not valid_distances.empty
    else 15.0
)

selected_distance = st.sidebar.slider(
    "Maximum distance from Princeton",
    min_value=0.0,
    max_value=maximum_distance,
    value=maximum_distance,
    step=0.5,
    format="%.1f miles",
)

affiliation_options = [
    "All",
    *sorted(assets["Affiliation Status"].dropna().unique().tolist()),
]

selected_affiliation = st.sidebar.selectbox(
    "Princeton-affiliation",
    options=affiliation_options,
)

program_options = [
    "All",
    *sorted(assets["Program Status"].dropna().unique().tolist()),
]

selected_program = st.sidebar.selectbox(
    "NJEDA recognition",
    options=program_options,
)

search_term = st.sidebar.text_input(
    "Keyword search",
    placeholder="e.g., wet lab, core facility, makerspace",
)

show_unknown_distance = st.sidebar.checkbox(
    "Include assets with no listed distance",
    value=True,
)

# Apply filters
filtered = assets.copy()

if selected_categories:
    filtered = filtered[
        filtered["Category"].isin(selected_categories)
    ]

if show_unknown_distance:
    filtered = filtered[
        filtered["Distance (mi)"].isna()
        | (filtered["Distance (mi)"] <= selected_distance)
    ]
else:
    filtered = filtered[
        filtered["Distance (mi)"].notna()
        & (filtered["Distance (mi)"] <= selected_distance)
    ]

if selected_affiliation != "All":
    filtered = filtered[
        filtered["Affiliation Status"] == selected_affiliation
    ]

if selected_program != "All":
    filtered = filtered[
        filtered["Program Status"] == selected_program
    ]

if search_term.strip():
    filtered = filtered[
        filtered["Search Text"].str.contains(
            search_term.strip().lower(),
            case=False,
            regex=False,
            na=False,
        )
    ]

filtered = filtered.sort_values(
    by=["Distance (mi)", "Organization Name"],
    na_position="last",
).reset_index(drop=True)

# Metrics
matching_assets = len(filtered)
mapped_locations = int(
    filtered[["Latitude", "Longitude"]].dropna().shape[0]
)
within_five_miles = int(
    (filtered["Distance (mi)"] <= 5).sum()
)
research_core_facilities = int(
    (filtered["Category"] == "Research Core Facility").sum()
)

metric_1, metric_2, metric_3, metric_4 = st.columns(4)

metric_1.metric("Matching resources", matching_assets)
metric_2.metric("Mapped locations", mapped_locations)
metric_3.metric("Within 5 miles", within_five_miles)
metric_4.metric("Research core facilities", research_core_facilities)

tab_map, tab_directory, tab_detail, tab_export = st.tabs(
    [
        "Map",
        "Directory list",
        "Resource detail",
        "Export list",
    ]
)

with tab_map:
    st.subheader("Innovation resource map")
    st.caption(
        "Hover over a marker for details. Each marker includes a link to "
        "open the recorded address in Google Maps."
    )

    legend_columns = st.columns(len(CATEGORY_COLORS))

    for column, (category, color) in zip(
        legend_columns,
        CATEGORY_COLORS.items(),
    ):
        color_css = f"rgb({color[0]}, {color[1]}, {color[2]})"

        column.markdown(
            f"<span style='color:{color_css}; font-size:18px;'>●</span> "
            f"{category}",
            unsafe_allow_html=True,
        )

    render_map(filtered)

    unmapped = filtered[
        filtered["Latitude"].isna()
        | filtered["Longitude"].isna()
    ]

    if not unmapped.empty:
        with st.expander(
            f"{len(unmapped)} record(s) lack map coordinates"
        ):
            st.write(
                "Add numeric Latitude and Longitude values to these rows in "
                "the CSV. No code edit is required."
            )

            st.dataframe(
                unmapped[
                    [
                        "Organization Name",
                        "Address",
                        "Category",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

with tab_directory:
    st.subheader("Filtered directory")

    directory_columns = [
        "Category",
        "Organization Name",
        "Address",
        "Distance (mi)",
        "Space Type",
        "Published Price",
        "Affiliation Status",
        "Program Status",
        "Website URL",
    ]

    st.dataframe(
        filtered[directory_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Distance (mi)": st.column_config.NumberColumn(
                "Distance from Princeton",
                format="%.1f mi",
            ),
            "Website URL": st.column_config.LinkColumn(
                "Website",
                display_text="Open",
            ),
            "Affiliation Status": st.column_config.TextColumn(
                "Princeton University affiliation",
            ),
        },
    )

with tab_detail:
    if filtered.empty:
        st.info("No resources match the active filters.")
    else:
        selected_name = st.selectbox(
            "Select a resource",
            options=filtered["Organization Name"].tolist(),
        )

        asset = filtered.loc[
            filtered["Organization Name"] == selected_name
        ].iloc[0]

        left_column, right_column = st.columns([1, 2])

        with left_column:
            st.subheader(asset["Organization Name"])
            st.write(f"**Category:** {asset['Category']}")
            st.write(f"**Address:** {asset['Address']}")

            if pd.notna(asset["Distance (mi)"]):
                st.write(
                    "**Distance from Princeton University:** "
                    f"{asset['Distance (mi)']:.1f} miles"
                )
            else:
                st.write(
                    "**Distance from Princeton University:** Not listed"
                )

            if asset["Website URL"]:
                website_url = html.escape(
                    asset["Website URL"],
                    quote=True,
                )

                st.markdown(
                    f"""
                    <a class="resource-action-button"
                       href="{website_url}"
                       target="_blank"
                       rel="noopener noreferrer">
                        Open website
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

            if asset["Address"]:
                maps_url = html.escape(
                    google_maps_url(asset["Address"]),
                    quote=True,
                )

                st.markdown(
                    f"""
                    <a class="resource-action-button"
                       href="{maps_url}"
                       target="_blank"
                       rel="noopener noreferrer">
                        Open in Google Maps
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

        with right_column:
            st.markdown("### Space and pricing")
            st.write(asset["Space Type"] or "Not listed")
            st.write(
                "**Published price (subject to change):** "
                f"{asset['Published Price'] or 'Not listed'}"
            )

            st.markdown(
                "### Princeton University affiliation or discounts"
            )
            st.write(
                asset["Princeton Affiliation Discount?"] or "Needs review"
            )

            st.markdown("### NJEDA recognition")
            st.write(
                asset[
                    "Accelerator / Incubator Program & NJEDA Recognition"
                ]
                or "No notes listed"
            )

with tab_export:
    st.subheader("Download filtered data")

    export_columns = [
        "Category",
        "Organization Name",
        "Address",
        "Latitude",
        "Longitude",
        "Distance from Princeton U (mi)",
        "Distance (mi)",
        "Space Type",
        "Published Price",
        "Princeton Affiliation Discount?",
        "Affiliation Status",
        "More Info / Website",
        "Website URL",
        "Accelerator / Incubator Program & NJEDA Recognition",
        "Program Status",
    ]

    export_df = filtered[export_columns].copy()

    st.download_button(
        label="Download filtered CSV",
        data=export_df.to_csv(index=False).encode("utf-8"),
        file_name="princeton_innovation_resources_filtered.csv",
        mime="text/csv",
        use_container_width=True,
    )

    with st.expander("Show filtered raw data"):
        st.dataframe(
            export_df,
            use_container_width=True,
            hide_index=True,
        )