import os
import time
import requests
import pandas as pd

OUTPUT_FILE = "italy_transit_stops.csv"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Bounding boxes for 5 main regions of Italy: (min_lat, min_lon, max_lat, max_lon)
ITALY_BBOXES = [
    ("North-West", (43.7, 6.6, 46.5, 10.0)),
    ("North-East", (44.5, 10.0, 47.1, 13.9)),
    ("Central", (41.2, 9.6, 44.5, 14.8)),
    ("South", (39.8, 13.8, 42.0, 18.6)),
    ("Islands", (36.6, 11.8, 41.4, 15.6)),
]

HEADERS = {
    "User-Agent": "TransitDataPipeline/1.0 (student_dev)",
    "Accept": "application/json"
}

def fetch_bbox_stops(bbox):
    """Fetches transport nodes inside a specific geographic bounding box."""
    s, w, n, e = bbox
    query = f"""
    [out:json][timeout:90];
    (
      node["highway"="bus_stop"]({s},{w},{n},{e});
      node["railway"="station"]({s},{w},{n},{e});
      node["railway"="halt"]({s},{w},{n},{e});
      node["railway"="tram_stop"]({s},{w},{n},{e});
      node["public_transport"="platform"]({s},{w},{n},{e});
    );
    out body;
    """
    response = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=120)
    response.raise_for_status()
    return response.json().get("elements", [])

def download_and_process_italy_stops():
    parsed_rows = []
    seen_ids = set()

    print("Step 1: Streaming live transport data for Italy in regional chunks...")

    for region_name, bbox in ITALY_BBOXES:
        print(f"[+] Querying region: {region_name}...")
        try:
            elements = fetch_bbox_stops(bbox)
            count = 0

            for elem in elements:
                node_id = str(elem.get("id"))
                if not node_id or node_id in seen_ids:
                    continue
                seen_ids.add(node_id)

                lat = elem.get("lat")
                lon = elem.get("lon")
                if lat is None or lon is None:
                    continue

                tags = elem.get("tags", {})

                common_name = tags.get("name") or tags.get("description") or f"Stop {node_id}"
                street_name = tags.get("addr:street") or tags.get("highway") or "Public Transport Network"
                town_name = tags.get("addr:city") or tags.get("addr:town") or tags.get("operator") or "Italy Region"

                parsed_rows.append({
                    "stop_id": node_id,
                    "common_name": common_name,
                    "street_name": street_name,
                    "town_name": town_name,
                    "lat": float(lat),
                    "lon": float(lon)
                })
                count += 1

            print(f" -> Fetched {count} unique stops from {region_name}.")
            time.sleep(1.5)  # Respect Overpass rate limits

        except Exception as e:
            print(f" [!] Warning: Failed fetching {region_name}: {e}. Retrying after 3s...")
            time.sleep(3)
            continue

    if not parsed_rows:
        print("CRITICAL ERROR: No data extracted.")
        return

    # 2. Data Cleaning & Schema Alignment
    print("\nStep 2: Processing Italian stop data and generating schema...")
    df = pd.DataFrame(parsed_rows)

    # Deduplicate exact overlapping coordinates
    df = df.drop_duplicates(subset=["lat", "lon"]).reset_index(drop=True)

    # 3. Output CSV Construction
    processed_df = pd.DataFrame()
    processed_df['Index Number'] = [f"IT{i}" for i in range(len(df))]
    processed_df['Stop Number'] = df['stop_id']
    processed_df['Common Stop Name'] = df['common_name']
    processed_df['Street Name'] = df['street_name']
    processed_df['Town Name'] = df['town_name']

    # Round coordinates strictly to 4 decimal places
    processed_df['Latitude'] = df['lat'].round(4)
    processed_df['Longitude'] = df['lon'].round(4)

    # 4. Save to Disk
    processed_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    print(f"\nSUCCESS! Exported clean file to '{OUTPUT_FILE}' with {len(processed_df)} entries.")

if __name__ == "__main__":
    download_and_process_italy_stops()