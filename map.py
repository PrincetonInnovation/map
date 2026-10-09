from __future__ import annotations

import html
import math
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

# Fixed map center: Princeton University / Nassau Hall area.
PRINCETON_LATITUDE = 40.3487
PRINCETON_LONGITUDE = -74.6593
MAP_RADIUS_MILES = 15
MAP_INITIAL_ZOOM = 10.2

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
PRINCETON_ORANGE_RGB = [238, 127, 45]

CATEGORY_COLORS = {
    "Coworking": [0, 119, 139],
    "Wet/Dry Lab": [91, 135, 74],
    "Prototyping": [126, 84, 164],
    "Prototyping (Accelerator-members Only)": [214, 51, 132],
    "Coworking (Accelerator-members Only)": [190, 30, 45],
    "Research Core Facility": [238, 127, 45],
    "Innovation Center / Research Park": [255, 215, 0],
    "Incubator / Accelerator": [128, 85, 44],
}

REQUIRED_COLUMNS = [
    "Category",
    "Organization Name",
    "Address",
    "Status",
    "Space Type",
    "Published Price",
    "Princeton Affiliation?",
    "More Info / Website",
    "CSIT Vouchers Accepted?",
    "Accelerator / Incubator Program & NJEDA Recognition",
    "Latitude",
    "Longitude",
    "Last Verified",
]

# Optional legacy column. Distance is now calculated from Latitude/Longitude;
# this column is only used for rows that have no coordinates.
LEGACY_DISTANCE_COLUMN = "Distance from Princeton U (mi)"

CSIT_HELP = (
    "CSIT is the New Jersey Commission on Science, Innovation and Technology. "
    "Its Innovation Vouchers help eligible companies pay for work at "
    "approved facilities. Voucher acceptance is unconfirmed for most "
    "listings, so this filter returns only resources confirmed as accepting."
)
NJEDA_HELP = (
    "NJEDA is the New Jersey Economic Development Authority. 'Yes' means the "
    "resource is an approved NJ Ignite workspace or an NJEDA Strategic "
    "Innovation Center (SIC). Listings that only appear in NJEDA directories "
    "without approval are not counted."
)
AFFILIATION_HELP = (
    "'Yes' means a direct Princeton University connection, such as a "
    "Princeton facility, a founding partnership, or a stated preference for "
    "the Princeton community."
)


def stretch(render, *args, **kwargs):
    """
    Render a Streamlit element at full container width on any version.

    Newer Streamlit versions use width="stretch"; older versions use
    use_container_width=True. This tries the new form first.
    """
    try:
        return render(*args, width="stretch", **kwargs)
    except Exception:
        return render(*args, use_container_width=True, **kwargs)


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

            /* Hover-help tooltips (the "?" icons). They open outside the
               sidebar on a dark background, so the dark-gray paragraph rule
               above made them unreadable. These selectors only match
               Streamlit's help tooltips, not the map tooltip or page text. */
            [data-testid="stTooltipContent"],
            [data-testid="stTooltipContent"] p,
            [data-testid="stTooltipContent"] li,
            [data-testid="stTooltipContent"] span,
            [data-baseweb="tooltip"] p,
            [data-baseweb="tooltip"] li,
            [data-baseweb="tooltip"] span {{
                color: var(--white) !important;
                -webkit-text-fill-color: var(--white) !important;
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
                -webkit-text-fill-color: var(--princeton-orange-dark) !important;
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
                -webkit-text-fill-color: var(--princeton-orange-dark) !important;
                font-weight: 750 !important;
            }}

            .stTabs [data-baseweb="tab-highlight"] {{
                background-color: var(--princeton-orange) !important;
            }}

            [data-testid="stSidebarCollapsedControl"],
            [data-testid="stSidebarCollapsedControl"] button {{
                background-color: var(--princeton-orange-light) !important;
                border: 1px solid var(--princeton-orange) !important;
                border-radius: 0.35rem !important;
                color: var(--princeton-orange) !important;
                opacity: 1 !important;
            }}

            [data-testid="stSidebarCollapsedControl"] > div,
            [data-testid="stSidebarCollapsedControl"] > div > button,
            [data-testid="stSidebarCollapsedControl"] > div > button > div,
            [data-testid="stSidebarCollapsedControl"] > div > button span,
            [data-testid="stSidebarCollapsedControl"] > div > button svg,
            [data-testid="stSidebarCollapsedControl"] > div > button svg path,
            [data-testid="stSidebarCollapsedControl"] button *,
            [data-testid="stSidebarCollapsedControl"] button svg,
            [data-testid="stSidebarCollapsedControl"] button svg path {{
                color: var(--princeton-orange) !important;
                fill: var(--princeton-orange) !important;
                stroke: var(--princeton-orange) !important;
                -webkit-text-fill-color: var(--princeton-orange) !important;
                opacity: 1 !important;
            }}

            [data-testid="stSidebar"] button[kind="header"],
            [data-testid="stSidebar"] button[kind="header"] * {{
                color: var(--princeton-orange) !important;
                fill: var(--princeton-orange) !important;
                stroke: var(--princeton-orange) !important;
                -webkit-text-fill-color: var(--princeton-orange) !important;
                opacity: 1 !important;
            }}

            [data-testid="stSidebarCollapsedControl"]:hover,
            [data-testid="stSidebarCollapsedControl"] button:hover {{
                background-color: var(--princeton-orange) !important;
                border-color: var(--princeton-orange-dark) !important;
            }}

            [data-testid="stSidebarCollapsedControl"]:hover *,
            [data-testid="stSidebarCollapsedControl"] button:hover * {{
                color: var(--ink) !important;
                fill: var(--ink) !important;
                stroke: var(--ink) !important;
                -webkit-text-fill-color: var(--ink) !important;
            }}

            a {{
                color: var(--princeton-orange-dark);
                font-weight: 600;
            }}

            a:hover {{
                color: var(--ink);
            }}

            [data-testid="stDataFrame"],
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


def md(value: object) -> str:
    """
    Make data text safe to display with st.write / st.markdown.

    Streamlit treats text as Markdown, so "$300 ... $500" became a math
    formula and characters like * or _ could turn text bold or italic.
    A backslash before these characters makes them display literally.
    """
    return re.sub(r"([\\`*_$~\[\]<>#|])", r"\\\1", clean_text(value))


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
    """
    Convert descriptive Princeton Affiliation text into two filter values.

    Any entry beginning with "Yes" is classified as Yes.
    N/A, None at this time, blanks, and all other text are grouped under
    Not specified.
    """
    text = clean_text(note)
    lower_text = text.lower()

    if lower_text.startswith("yes"):
        return "Yes"

    return "Not specified"


def classify_program_status(note: object) -> str:
    """
    Convert the descriptive NJEDA column into two filter values.

    - Entries beginning with "NJ Ignite" or "SIC" are grouped as Yes.
    - "Partial" (listed in an NJEDA directory but not approved), "None",
      "Needs confirmation", blanks, and anything else are Not specified.
    """
    text = clean_text(note)
    lower_text = text.lower()

    if lower_text.startswith(("nj ignite", "sic")):
        return "Yes"

    return "Not specified"


def distance_from_princeton(latitude: float, longitude: float) -> float | None:
    """Straight-line (great-circle) distance in miles from Princeton."""
    if pd.isna(latitude) or pd.isna(longitude):
        return None

    earth_radius_miles = 3958.7613
    lat_1 = math.radians(PRINCETON_LATITUDE)
    lat_2 = math.radians(latitude)
    delta_lat = lat_2 - lat_1
    delta_lon = math.radians(longitude - PRINCETON_LONGITUDE)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_1) * math.cos(lat_2) * math.sin(delta_lon / 2) ** 2
    )
    return round(2 * earth_radius_miles * math.asin(math.sqrt(a)), 1)


def category_color(category: object) -> list[int]:
    """Map each resource category to its marker RGB color."""
    return CATEGORY_COLORS.get(clean_text(category), DEFAULT_MARKER_COLOR)


def google_maps_url(address: object) -> str:
    """Create a direct address-search link for Google Maps."""
    return (
        "https://www.google.com/maps/search/?api=1&query="
        f"{quote(clean_text(address))}"
    )


def radius_circle_coordinates(
    center_latitude: float,
    center_longitude: float,
    radius_miles: float,
    points: int = 180,
) -> list[list[float]]:
    """Create longitude/latitude coordinates for a geodesic circle."""
    earth_radius_miles = 3958.7613
    angular_distance = radius_miles / earth_radius_miles
    center_latitude_radians = math.radians(center_latitude)
    center_longitude_radians = math.radians(center_longitude)
    coordinates = []

    for point_index in range(points + 1):
        bearing = 2 * math.pi * point_index / points
        latitude_radians = math.asin(
            math.sin(center_latitude_radians) * math.cos(angular_distance)
            + math.cos(center_latitude_radians)
            * math.sin(angular_distance)
            * math.cos(bearing)
        )
        longitude_radians = center_longitude_radians + math.atan2(
            math.sin(bearing)
            * math.sin(angular_distance)
            * math.cos(center_latitude_radians),
            math.cos(angular_distance)
            - math.sin(center_latitude_radians)
            * math.sin(latitude_radians),
        )
        coordinates.append(
            [
                math.degrees(longitude_radians),
                math.degrees(latitude_radians),
            ]
        )

    return coordinates


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------


@st.cache_data
def load_assets(csv_path: str) -> pd.DataFrame:
    """Load the asset CSV with UTF-8 and Windows-1252 compatibility."""
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

    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    # Calculate distance from coordinates so every entry uses the same
    # straight-line measure as the 15-mile ring. Fall back to a typed
    # distance only for rows without coordinates.
    df["Distance (mi)"] = [
        distance_from_princeton(lat, lon)
        for lat, lon in zip(df["Latitude"], df["Longitude"])
    ]
    if LEGACY_DISTANCE_COLUMN in df.columns:
        typed_distance = df[LEGACY_DISTANCE_COLUMN].map(extract_distance)
        df["Distance (mi)"] = df["Distance (mi)"].fillna(typed_distance)
    df["Distance (mi)"] = pd.to_numeric(df["Distance (mi)"], errors="coerce")

    df["Status"] = df["Status"].replace("", "Open")
    df["Website URL"] = df["More Info / Website"].map(extract_first_url)
    df["Affiliation Status"] = df[
        "Princeton Affiliation?"
    ].map(classify_affiliation)
    df["Program Status"] = df[
        "Accelerator / Incubator Program & NJEDA Recognition"
    ].map(classify_program_status)

    searchable_columns = [
        "Category",
        "Organization Name",
        "Address",
        "Status",
        "Space Type",
        "Published Price",
        "Princeton Affiliation?",
        "CSIT Vouchers Accepted?",
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


def format_distance(value: object) -> str:
    return f"{value:.1f} miles" if pd.notna(value) else "Not listed"


def build_marker_groups(mapped: pd.DataFrame) -> pd.DataFrame:
    """
    Combine resources that share a location into one marker.

    Many Princeton core facilities sit in the same building, so separate
    markers would stack exactly on top of each other and hide all but one.
    Coordinates are rounded to 4 decimal places (about 10 meters).
    """
    mapped = mapped.copy()
    mapped["lat_key"] = mapped["Latitude"].round(4)
    mapped["lon_key"] = mapped["Longitude"].round(4)

    markers = []
    for _, group in mapped.groupby(["lat_key", "lon_key"], sort=False):
        first = group.iloc[0]
        all_planned = (group["Status"] == "Planned").all()
        main_category = group["Category"].mode().iloc[0]
        color = category_color(main_category) + [130 if all_planned else 255]

        # Streamlit shows tooltip field values as plain text (any HTML tags
        # would appear literally), so lines are separated with newline
        # characters. The tooltip style below ("whiteSpace": "pre-line")
        # turns those newlines into line breaks.
        if len(group) == 1:
            title = first["Organization Name"]
            status = (
                "Planned (not yet open)"
                if first["Status"] == "Planned"
                else first["Status"]
            )
            lines = [
                f"Category: {first['Category']}",
                f"Status: {status}",
                f"Address: {first['Address']}",
                f"Distance: {format_distance(first['Distance (mi)'])}",
                "CSIT vouchers: "
                f"{first['CSIT Vouchers Accepted?'] or 'Unknown'}",
                f"NJEDA recognized: {first['Program Status']}",
            ]
        else:
            title = f"{len(group)} resources at this location"
            lines = [
                f"Address: {group['Address'].mode().iloc[0]}",
                f"Distance: {format_distance(first['Distance (mi)'])}",
                "",
            ] + [f"• {name}" for name in group["Organization Name"]]
        body = "\n".join(lines)

        markers.append(
            {
                "latitude": group["Latitude"].mean(),
                "longitude": group["Longitude"].mean(),
                "marker_color": color,
                "radius": 280 + 70 * (len(group) - 1),
                "tooltip_title": title,
                "tooltip_body": body,
            }
        )

    return pd.DataFrame(markers)


def render_legend(filtered_assets: pd.DataFrame) -> None:
    """Show only the categories present in the current results."""
    present = set(filtered_assets["Category"])
    items = [
        (category, color)
        for category, color in CATEGORY_COLORS.items()
        if category in present
    ]
    items += [
        (category, DEFAULT_MARKER_COLOR)
        for category in sorted(present - set(CATEGORY_COLORS))
        if category
    ]

    if not items:
        return

    spans = "".join(
        "<span style='white-space:nowrap; margin-right:1.4rem;'>"
        f"<span style='color:rgb({c[0]}, {c[1]}, {c[2]}); font-size:18px;'>"
        f"&#9679;</span> {html.escape(category)}</span>"
        for category, c in items
    )
    st.markdown(
        "<div style='display:flex; flex-wrap:wrap; row-gap:0.3rem; "
        f"margin-bottom:0.6rem;'>{spans}</div>"
        "<div style='font-size:0.85rem; color:var(--medium-gray);'>"
        "Faded markers are planned facilities that are not yet open. "
        "Larger markers group several resources in the same building."
        "</div>",
        unsafe_allow_html=True,
    )


def render_map(filtered_assets: pd.DataFrame) -> None:
    """Render a map centered on Princeton University with a 15-mile ring."""
    mapped = filtered_assets.dropna(subset=["Latitude", "Longitude"]).copy()
    markers = build_marker_groups(mapped) if not mapped.empty else mapped

    circle_coordinates = radius_circle_coordinates(
        center_latitude=PRINCETON_LATITUDE,
        center_longitude=PRINCETON_LONGITUDE,
        radius_miles=MAP_RADIUS_MILES,
    )

    ring_data = pd.DataFrame(
        [
            {
                "start": circle_coordinates[index],
                "end": circle_coordinates[index + 1],
            }
            for index in range(len(circle_coordinates) - 1)
        ]
    )

    university_data = pd.DataFrame(
        [
            {
                "name": "Princeton University",
                "longitude": PRINCETON_LONGITUDE,
                "latitude": PRINCETON_LATITUDE,
            }
        ]
    )

    radius_layer = pdk.Layer(
        "GreatCircleLayer",
        data=ring_data,
        get_source_position="start",
        get_target_position="end",
        get_source_color=PRINCETON_ORANGE_RGB,
        get_target_color=PRINCETON_ORANGE_RGB,
        get_width=2,
        width_min_pixels=1,
        pickable=False,
    )

    university_layer = pdk.Layer(
        "ScatterplotLayer",
        data=university_data,
        get_position="[longitude, latitude]",
        get_fill_color=[29, 29, 27],
        get_radius=375,
        radius_min_pixels=8,
        radius_max_pixels=16,
        pickable=False,
        stroked=True,
        get_line_color=[255, 255, 255],
        line_width_min_pixels=2,
    )

    layers = [radius_layer, university_layer]

    if not mapped.empty:
        marker_layer = pdk.Layer(
            "ScatterplotLayer",
            data=markers,
            get_position="[longitude, latitude]",
            get_fill_color="marker_color",
            get_radius="radius",
            radius_min_pixels=8,
            radius_max_pixels=28,
            pickable=True,
            stroked=True,
            get_line_color=[255, 255, 255],
            line_width_min_pixels=1,
        )
        layers.append(marker_layer)

    tooltip = {
        "html": "<b>{tooltip_title}</b><br/>{tooltip_body}",
        "style": {
            "backgroundColor": "#FFFFFF",
            "color": "#1D1D1B",
            "fontSize": "13px",
            "padding": "10px",
            "maxWidth": "340px",
            "whiteSpace": "pre-line",
        },
    }

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=PRINCETON_LATITUDE,
            longitude=PRINCETON_LONGITUDE,
            zoom=MAP_INITIAL_ZOOM,
            pitch=0,
        ),
        map_provider="carto",
        map_style=CARTO_POSITRON_STYLE,
        tooltip=tooltip,
    )

    stretch(st.pydeck_chart, deck, height=650)

    if mapped.empty:
        st.info(
            "No mapped facilities match the current filters. The map remains "
            "centered on Princeton University and shows the 15-mile radius."
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

st.sidebar.header("Directory filters")

categories = sorted(assets["Category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Space category",
    options=categories,
    default=categories,
)

valid_distances = assets["Distance (mi)"].dropna()
maximum_distance = (
    float(valid_distances.max()) if not valid_distances.empty else 15.0
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
    "Yes",
    "Not specified",
]
selected_affiliation = st.sidebar.selectbox(
    "Princeton-Affiliated Resource",
    options=affiliation_options,
    help=AFFILIATION_HELP,
)

program_options = [
    "All",
    "Yes",
    "Not specified",
]
selected_program = st.sidebar.selectbox(
    "NJEDA-Recognized Resource",
    options=program_options,
    help=NJEDA_HELP,
)

search_term = st.sidebar.text_input(
    "Keyword search",
    placeholder="e.g., coworking, core facility, makerspace",
    help="Simple keyword search.",
)

limit_to_csit_vouchers = st.sidebar.checkbox(
    "Limit to resources accepting CSIT Vouchers",
    value=False,
    help=CSIT_HELP,
)

include_planned = st.sidebar.checkbox(
    "Include planned facilities (not yet open)",
    value=True,
)

filtered = assets.copy()

if selected_categories:
    filtered = filtered[filtered["Category"].isin(selected_categories)]

if limit_to_csit_vouchers:
    # Treat any value that begins with "Yes" as voucher-accepting. This allows
    # the CSV to contain values such as "Yes", "Yes — confirmed", or
    # "Yes — confirm facility-specific applicability".
    filtered = filtered[
        filtered["CSIT Vouchers Accepted?"].str.strip().str.lower().str.startswith(
            "yes",
            na=False,
        )
    ]

if not include_planned:
    filtered = filtered[filtered["Status"] != "Planned"]

# Resources without a single location (such as campus-wide services) have
# no distance and are always kept.
filtered = filtered[
    filtered["Distance (mi)"].isna()
    | (filtered["Distance (mi)"] <= selected_distance)
]

if selected_affiliation != "All":
    filtered = filtered[
        filtered["Affiliation Status"] == selected_affiliation
    ]

if selected_program != "All":
    filtered = filtered[filtered["Program Status"] == selected_program]

for word in search_term.lower().split():
    filtered = filtered[
        filtered["Search Text"].str.contains(
            word,
            case=False,
            regex=False,
            na=False,
        )
    ]

filtered = filtered.sort_values(
    by=["Distance (mi)", "Organization Name"],
    na_position="last",
).reset_index(drop=True)

matching_assets = len(filtered)
mapped_locations = int(filtered[["Latitude", "Longitude"]].dropna().shape[0])
within_five_miles = int((filtered["Distance (mi)"] <= 5).sum())
research_core_facilities = int(
    (filtered["Category"] == "Research Core Facility").sum()
)

metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric("Matching resources", matching_assets)
metric_2.metric("Mapped locations", mapped_locations)
metric_3.metric("Within 5 miles", within_five_miles)
metric_4.metric("Research core facilities", research_core_facilities)

tab_map, tab_directory, tab_detail, tab_export = st.tabs(
    ["Map", "Directory list", "Resource detail", "Export list"]
)

with tab_map:
    st.subheader("Innovation resource map")
    st.caption(
        "The map is centered on Princeton University with the "
        "orange ring marking a 15-mile radius. Hover over a marker for "
        "details; links and contacts are on the Resource detail tab."
    )

    render_legend(filtered)
    render_map(filtered)

    unmapped = filtered[
        filtered["Latitude"].isna() | filtered["Longitude"].isna()
    ]
    if not unmapped.empty:
        with st.expander(
            f"{len(unmapped)} resource(s) not shown on the map"
        ):
            st.write(
                "These resources have no single map location (for example, "
                "campus-wide services). They still appear in the directory, "
                "detail, and export tabs."
            )
            stretch(
                st.dataframe,
                unmapped[["Organization Name", "Address", "Category"]],
                hide_index=True,
            )

with tab_directory:
    st.subheader("Filtered directory")

    directory_columns = [
        "Category",
        "Organization Name",
        "Status",
        "Address",
        "Distance (mi)",
        "Space Type",
        "Published Price",
        "Affiliation Status",
        "CSIT Vouchers Accepted?",
        "Program Status",
        "Website URL",
    ]

    stretch(
        st.dataframe,
        filtered[directory_columns],
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
            "CSIT Vouchers Accepted?": st.column_config.TextColumn(
                "CSIT vouchers",
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
            st.subheader(md(asset["Organization Name"]))
            st.write(f"**Category:** {md(asset['Category'])}")
            if asset["Status"] == "Planned":
                st.warning("Planned facility: not yet open.")
            st.write(f"**Address:** {md(asset['Address'])}")

            if pd.notna(asset["Distance (mi)"]):
                st.write(
                    "**Distance from Princeton University:** "
                    f"{asset['Distance (mi)']:.1f} miles (straight line)"
                )
            else:
                st.write(
                    "**Distance from Princeton University:** "
                    "No single location"
                )

            st.caption(
                "Last verified: "
                f"{md(asset['Last Verified']) or 'Not yet recorded'}"
            )

            if asset["Website URL"]:
                website_url = html.escape(asset["Website URL"], quote=True)
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
            st.write(md(asset["Space Type"]) or "Not listed")
            st.write(
                "**Published price (subject to change):** "
                f"{md(asset['Published Price']) or 'Not listed'}"
            )

            st.markdown("### Princeton University affiliation or discounts")
            st.write(
                md(asset["Princeton Affiliation?"]) or "Needs review"
            )

            st.markdown("### CSIT vouchers")
            st.write(
                md(asset["CSIT Vouchers Accepted?"])
                or "Unknown — confirm directly"
            )

            st.markdown("### NJEDA recognized")
            st.write(
                md(
                    asset[
                        "Accelerator / Incubator Program & NJEDA Recognition"
                    ]
                )
                or "No notes listed"
            )

with tab_export:
    st.subheader("Download filtered data")

    export_columns = [
        "Category",
        "Organization Name",
        "Status",
        "Address",
        "Latitude",
        "Longitude",
        "Distance (mi)",
        "Space Type",
        "Published Price",
        "Princeton Affiliation?",
        "Affiliation Status",
        "More Info / Website",
        "Website URL",
        "CSIT Vouchers Accepted?",
        "Accelerator / Incubator Program & NJEDA Recognition",
        "Program Status",
        "Last Verified",
    ]

    export_df = filtered[export_columns].copy()

    # "utf-8-sig" adds a marker that tells Excel the file is UTF-8, so
    # characters such as dashes and accents display correctly.
    stretch(
        st.download_button,
        label="Download filtered CSV",
        data=export_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="princeton_innovation_resources_filtered.csv",
        mime="text/csv",
    )

    with st.expander("Show filtered raw data"):
        stretch(st.dataframe, export_df, hide_index=True)
