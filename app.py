from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pandas as pd
import os
import math
from datetime import datetime
from zoneinfo import ZoneInfo

# ============================================================
# NEERVIZHI - GROUNDWATER INTELLIGENCE PLATFORM
# ============================================================

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CSV_FILE = os.path.join(
    BASE_DIR,
    "groundwater_with_weather.csv"
)

if not os.path.exists(CSV_FILE):
    raise FileNotFoundError(
        f"Dataset not found: {CSV_FILE}"
    )

df = pd.read_csv(CSV_FILE)


# ============================================================
# COLUMN DETECTION
# ============================================================

def normalize_column_name(value):
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("%", "percent")
    )


def get_columns(dataframe):

    columns = {
        "state": None,
        "district": None,
        "block": None,
        "village": None,
        "latitude": None,
        "longitude": None,
        "date": None,
        "depth": None,
        "rainfall": None,
        "temperature": None,
        "humidity": None,
        "wind_speed": None
    }

    normalized = {}

    for column in dataframe.columns:

        normalized[
            normalize_column_name(column)
        ] = column

    candidates = {

        "state": [
            "state"
        ],

        "district": [
            "district"
        ],

        "block": [
            "block",
            "taluk",
            "taluka"
        ],

        "village": [
            "village"
        ],

        "latitude": [
            "latitude",
            "lat"
        ],

        "longitude": [
            "longitude",
            "lon",
            "lng"
        ],

        "date": [
            "date",
            "observation_date",
            "observationdate"
        ],

        "depth": [
            "wl_mbgl",
            "wlmbgl",
            "wl_mbgl",
            "wlmbgl",
            "wl",
            "depth",
            "groundwater_depth",
            "groundwaterdepth",
            "water_level",
            "waterlevel",
            "water_level_mbgl",
            "waterlevelmbgl",
            "water_level_mbgl"
        ],

        "rainfall": [
            "rainfall",
            "rain",
            "rain_mm",
            "rainfall_mm",
            "precipitation",
            "precipitation_mm"
        ],

        "temperature": [
            "temperature",
            "temp",
            "temperature_c",
            "temperature_celsius",
            "temp_c"
        ],

        "humidity": [
            "humidity",
            "relative_humidity",
            "humidity_percent",
            "relativehumidity"
        ],

        "wind_speed": [
            "wind_speed",
            "windspeed",
            "wind_speed_kmh",
            "wind_speed_kph",
            "wind_kmh",
            "wind_kph",
            "wind_speed_mph",
            "wind_speed_mps",
            "wind_mps",
            "wind",
            "windspeed_kmh",
            "windspeed_kph",
            "wind_speed_km_h",
            "wind_speed_kmhr"
        ]
    }

    for key, names in candidates.items():

        for name in names:

            normalized_name = normalize_column_name(name)

            if normalized_name in normalized:

                columns[key] = normalized[
                    normalized_name
                ]

                break

    return columns


COL = get_columns(df)


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required = [
    "state",
    "district",
    "block",
    "village",
    "latitude",
    "longitude",
    "date",
    "depth"
]

missing = [
    key
    for key in required
    if COL[key] is None
]

if missing:

    raise ValueError(
        "Required columns missing: "
        + ", ".join(missing)
        + "\nAvailable columns: "
        + ", ".join(
            map(str, df.columns)
        )
    )


# ============================================================
# CLEAN DATA
# ============================================================

for column in df.columns:

    if df[column].dtype == "object":

        df[column] = (
            df[column]
            .astype(str)
            .str.strip()
            .replace({
                "nan": None,
                "NaN": None,
                "None": None,
                "none": None,
                "": None
            })
        )


# ============================================================
# DATE
# ============================================================

df[COL["date"]] = pd.to_datetime(
    df[COL["date"]],
    errors="coerce",
    dayfirst=True
)


# ============================================================
# NUMERIC COLUMNS
# ============================================================

for key in [
    "latitude",
    "longitude",
    "depth",
    "rainfall",
    "temperature",
    "humidity",
    "wind_speed"
]:

    if COL[key] is not None:

        df[COL[key]] = pd.to_numeric(
            df[COL[key]],
            errors="coerce"
        )


# ============================================================
# REMOVE INVALID LOCATION ROWS
# ============================================================

location_columns = [
    COL["state"],
    COL["district"],
    COL["block"],
    COL["village"]
]

df = df.dropna(
    subset=location_columns
).copy()


for column in location_columns:

    df = df[
        df[column]
        .astype(str)
        .str.strip()
        .ne("")
    ]


df = (
    df
    .sort_values(
        COL["date"],
        na_position="last"
    )
    .reset_index(drop=True)
)


# ============================================================
# DATE / TIME
# ============================================================

def get_current_date():

    return datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%Y-%m-%d")


def get_current_datetime():

    return datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# SAFE VALUE
# ============================================================

def clean_value(value):

    if value is None:
        return None

    try:

        if pd.isna(value):
            return None

    except Exception:
        pass

    return value


# ============================================================
# SAFE NUMBER
# ============================================================

def safe_number(value):

    if value is None:
        return None

    try:

        value = float(value)

        if math.isnan(value):
            return None

        if math.isinf(value):
            return None

        return value

    except Exception:

        return None


# ============================================================
# WIND SPEED
# ============================================================

def get_wind_speed(row):

    """
    Reads wind speed from the detected CSV column.

    Supports:
        km/h
        kph
        m/s
        mph

    Everything returned to frontend is km/h.
    """

    if COL["wind_speed"] is None:

        return None

    raw = row[COL["wind_speed"]]

    value = safe_number(raw)

    if value is None:

        return None

    column_name = normalize_column_name(
        COL["wind_speed"]
    )

    # --------------------------------------------------------
    # METERS PER SECOND -> KM/H
    # --------------------------------------------------------

    if (
        "mps" in column_name
        or "m_s" in column_name
        or "meter" in column_name
    ):

        value = value * 3.6

    # --------------------------------------------------------
    # MILES PER HOUR -> KM/H
    # --------------------------------------------------------

    elif (
        "mph" in column_name
        or "mile" in column_name
    ):

        value = value * 1.60934

    # --------------------------------------------------------
    # OTHERWISE ASSUME KM/H
    # --------------------------------------------------------

    return round(
        value,
        2
    )


# ============================================================
# UNIQUE VALUES
# ============================================================

def unique_values(series):

    if series is None:
        return []

    vals = (
        series
        .dropna()
        .astype(str)
        .str.strip()
    )

    return sorted([
        value
        for value in vals.unique()
        if value
        and value.lower()
        not in (
            "nan",
            "none"
        )
    ])


# ============================================================
# FILTER DATA
# ============================================================

def filter_data(
    state=None,
    district=None,
    block=None,
    village=None,
    date=None
):

    result = df.copy()

    filters = [
        ("state", state),
        ("district", district),
        ("block", block),
        ("village", village)
    ]

    for key, value in filters:

        if value:

            result = result[
                result[COL[key]]
                .astype(str)
                .str.strip()
                .str.casefold()
                ==
                str(value)
                .strip()
                .casefold()
            ]

    if date:

        requested = pd.to_datetime(
            date,
            errors="coerce"
        )

        if not pd.isna(requested):

            result = result[
                result[COL["date"]]
                .dt.date
                ==
                requested.date()
            ]

    return result


# ============================================================
# GROUNDWATER STATUS
# ============================================================

def calculate_status(depth):

    if depth is None:
        return "Unknown"

    try:

        depth = float(depth)

    except Exception:

        return "Unknown"

    if depth <= 3:
        return "Good"

    if depth <= 6:
        return "Moderate"

    if depth <= 10:
        return "Low"

    return "Critical"


# ============================================================
# WIND CONDITION
# ============================================================

def wind_condition(value):

    value = safe_number(value)

    if value is None:

        return "No wind data"

    if value < 1:

        return "Calm"

    if value < 10:

        return "Light wind"

    if value < 20:

        return "Moderate wind"

    if value < 30:

        return "Strong wind"

    return "Very strong wind"


# ============================================================
# BUILD DASHBOARD RESPONSE
# ============================================================

def build_dashboard_row(row):

    depth = safe_number(
        row[COL["depth"]]
    )

    wind_speed = get_wind_speed(
        row
    )

    weather = {

        "rainfall":
            safe_number(
                row[COL["rainfall"]]
            )
            if COL["rainfall"]
            else None,

        "temperature":
            safe_number(
                row[COL["temperature"]]
            )
            if COL["temperature"]
            else None,

        "humidity":
            safe_number(
                row[COL["humidity"]]
            )
            if COL["humidity"]
            else None,

        "wind_speed":
            wind_speed
    }

    observation_date = None

    if not pd.isna(
        row[COL["date"]]
    ):

        observation_date = (
            pd.Timestamp(
                row[COL["date"]]
            )
            .strftime("%Y-%m-%d")
        )

    return {

        "success": True,

        "date":
            get_current_date(),

        "observation_date":
            observation_date,

        "location": {

            "state":
                clean_value(
                    row[COL["state"]]
                ),

            "district":
                clean_value(
                    row[COL["district"]]
                ),

            "block":
                clean_value(
                    row[COL["block"]]
                ),

            "village":
                clean_value(
                    row[COL["village"]]
                ),

            "latitude":
                safe_number(
                    row[COL["latitude"]]
                ),

            "longitude":
                safe_number(
                    row[COL["longitude"]]
                )
        },

        "groundwater": {

            "depth":
                depth,

            "status":
                calculate_status(
                    depth
                )
        },

        "weather": weather,

        "wind_condition":
            wind_condition(
                wind_speed
            )
    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    template_path = os.path.join(
        BASE_DIR,
        "templates",
        "index.html"
    )

    root_path = os.path.join(
        BASE_DIR,
        "index.html"
    )

    if os.path.exists(
        template_path
    ):

        return send_from_directory(
            os.path.join(
                BASE_DIR,
                "templates"
            ),
            "index.html"
        )

    if os.path.exists(
        root_path
    ):

        return send_from_directory(
            BASE_DIR,
            "index.html"
        )

    return jsonify({

        "application":
            "நீர்விழி - Groundwater Intelligence Platform",

        "status":
            "running",

        "message":
            "Backend is running.",

        "endpoints": [

            "/api/health",
            "/api/options",
            "/api/districts",
            "/api/blocks",
            "/api/villages",
            "/api/dashboard",
            "/api/history",
            "/api/weather"

        ]
    })


# ============================================================
# HEALTH
# ============================================================

@app.route("/api/health")
def health():

    return jsonify({

        "status":
            "ok",

        "records":
            int(len(df)),

        "states":
            int(
                df[
                    COL["state"]
                ].nunique()
            ),

        "current_date":
            get_current_date(),

        "current_datetime":
            get_current_datetime(),

        "wind_column":
            COL["wind_speed"],

        "columns":
            list(
                df.columns
            )
    })


# ============================================================
# OPTIONS
# ============================================================

@app.route("/api/options")
def options():

    states = unique_values(
        df[COL["state"]]
    )

    return jsonify({

        "states":
            states,

        "record_count":
            int(len(df)),

        "states_count":
            len(states),

        "current_date":
            get_current_date(),

        "current_datetime":
            get_current_datetime()
    })


# ============================================================
# DISTRICTS
# ============================================================

@app.route("/api/districts")
def districts():

    state = request.args.get(
        "state",
        ""
    ).strip()

    return jsonify({

        "districts":
            unique_values(
                filter_data(
                    state=state
                )[COL["district"]]
            )
            if state
            else []
    })


# ============================================================
# BLOCKS
# ============================================================

@app.route("/api/blocks")
def blocks():

    state = request.args.get(
        "state",
        ""
    ).strip()

    district = request.args.get(
        "district",
        ""
    ).strip()

    return jsonify({

        "blocks":
            unique_values(
                filter_data(
                    state=state,
                    district=district
                )[COL["block"]]
            )
            if state and district
            else []
    })


# ============================================================
# VILLAGES
# ============================================================

@app.route("/api/villages")
def villages():

    state = request.args.get(
        "state",
        ""
    ).strip()

    district = request.args.get(
        "district",
        ""
    ).strip()

    block = request.args.get(
        "block",
        ""
    ).strip()

    return jsonify({

        "villages":
            unique_values(
                filter_data(
                    state=state,
                    district=district,
                    block=block
                )[COL["village"]]
            )
            if state
            and district
            and block
            else []
    })


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/api/dashboard")
def dashboard():

    filtered = filter_data(

        state=request.args.get(
            "state",
            ""
        ).strip(),

        district=request.args.get(
            "district",
            ""
        ).strip(),

        block=request.args.get(
            "block",
            ""
        ).strip(),

        village=request.args.get(
            "village",
            ""
        ).strip(),

        date=request.args.get(
            "date",
            ""
        ).strip()
    )

    if filtered.empty:

        return jsonify({

            "error":
                "No groundwater observation found for the selected location/date."

        }), 404

    filtered = (
        filtered
        .sort_values(
            COL["date"],
            na_position="last"
        )
    )

    response = build_dashboard_row(
        filtered.iloc[-1]
    )

    response.update({

        "record_count":
            int(len(df)),

        "matching_records":
            int(len(filtered)),

        "states_count":
            int(
                df[
                    COL["state"]
                ].nunique()
            ),

        "current_date":
            get_current_date(),

        "current_datetime":
            get_current_datetime()
    })

    return jsonify(
        response
    )


# ============================================================
# HISTORY
# ============================================================

@app.route("/api/history")
def history():

    filtered = filter_data(

        state=request.args.get(
            "state",
            ""
        ).strip(),

        district=request.args.get(
            "district",
            ""
        ).strip(),

        block=request.args.get(
            "block",
            ""
        ).strip(),

        village=request.args.get(
            "village",
            ""
        ).strip()
    )

    filtered = (
        filtered
        .dropna(
            subset=[
                COL["date"],
                COL["depth"]
            ]
        )
        .sort_values(
            COL["date"]
        )
        .copy()
    )

    labels = [

        pd.Timestamp(
            value
        ).strftime(
            "%d-%m-%Y"
        )

        for value
        in filtered[
            COL["date"]
        ]
    ]

    values = [

        safe_number(
            value
        )

        for value
        in filtered[
            COL["depth"]
        ]
    ]

    pairs = [

        (label, value)

        for label, value
        in zip(
            labels,
            values
        )

        if value is not None
    ]

    return jsonify({

        "labels":
            [
                item[0]
                for item in pairs
            ],

        "values":
            [
                item[1]
                for item in pairs
            ],

        "count":
            len(pairs),

        "current_date":
            get_current_date(),

        "current_datetime":
            get_current_datetime()
    })


# ============================================================
# WEATHER
# ============================================================

@app.route("/api/weather")
def weather():

    filtered = filter_data(

        state=request.args.get(
            "state",
            ""
        ).strip(),

        district=request.args.get(
            "district",
            ""
        ).strip(),

        block=request.args.get(
            "block",
            ""
        ).strip(),

        village=request.args.get(
            "village",
            ""
        ).strip()
    )

    if filtered.empty:

        return jsonify({

            "error":
                "No location found."

        }), 404

    row = (
        filtered
        .sort_values(
            COL["date"],
            na_position="last"
        )
        .iloc[-1]
    )

    wind = get_wind_speed(
        row
    )

    observation_date = None

    if not pd.isna(
        row[COL["date"]]
    ):

        observation_date = (
            pd.Timestamp(
                row[COL["date"]]
            )
            .strftime(
                "%Y-%m-%d"
            )
        )

    return jsonify({

        "success":
            True,

        "rainfall":
            safe_number(
                row[COL["rainfall"]]
            )
            if COL["rainfall"]
            else None,

        "temperature":
            safe_number(
                row[COL["temperature"]]
            )
            if COL["temperature"]
            else None,

        "humidity":
            safe_number(
                row[COL["humidity"]]
            )
            if COL["humidity"]
            else None,

        "wind_speed":
            wind,

        "wind_condition":
            wind_condition(
                wind
            ),

        "observation_date":
            observation_date,

        "current_date":
            get_current_date(),

        "current_datetime":
            get_current_datetime()
    })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "நீர்விழி - GROUNDWATER INTELLIGENCE PLATFORM"
    )

    print("=" * 70)

    print(
        "Dataset:",
        CSV_FILE
    )

    print(
        "Records:",
        len(df)
    )

    print(
        "States:",
        df[
            COL["state"]
        ].nunique()
    )

    print(
        "Detected wind column:",
        COL["wind_speed"]
    )

    print(
        "Detected temperature column:",
        COL["temperature"]
    )

    print(
        "Detected humidity column:",
        COL["humidity"]
    )

    print(
        "Detected rainfall column:",
        COL["rainfall"]
    )

    print(
        "Server: http://127.0.0.1:5000"
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )