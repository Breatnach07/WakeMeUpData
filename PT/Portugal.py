import os
import requests
import pandas as pd

def download_and_process_pt_stops(output_file="portugal_transit_stops.csv"):
    temp_raw_file = "raw_pt_stops.json"
    overpass_url = "https://overpass-api.de/api/interpreter"

    # Overpass QL Query strictly targeting ISO3166-1 Portugal
    query = """
    [out:json][timeout:180];
    area["ISO3166-1"="PT"]["admin_level"="2"]->.searchArea;
    (
      node["highway"="bus_stop"](area.searchArea);
      node["railway"="station"](area.searchArea);
      node["railway"="halt"](area.searchArea);
      node["railway"="tram_stop"](area.searchArea);
      node["public_transport"="platform"](area.searchArea);
    );
    out body;
    """

    headers = {
        "User-Agent": "TransitDataPipeline/1.0 (student_dev)",
        "Accept": "application/json"
    }

    # 1. Download Core Data from Overpass
    try:
        print("Step 1: Querying Overpass API for Portugal transit stops...")
        response = requests.post(overpass_url, data={"data": query}, headers=headers, timeout=200)
        response.raise_for_status()
        
        data = response.json()
        elements = data.get("elements", [])
        print(f"-> Download complete. Retrived {len(elements)} raw transit nodes.")

    except Exception as e:
        print(f"CRITICAL NETWORK ERROR: {e}")
        return

    # 2. Hardened Filtering and Structure Extraction
    try:
        print("\nStep 2: Processing Portuguese stop data...")
        parsed_rows = []

        for idx, elem in enumerate(elements):
            lat = elem.get("lat")
            lon = elem.get("lon")
            if lat is None or lon is None:
                continue

            tags = elem.get("tags", {})
            stop_id = str(elem.get("id"))

            # Extract tags with robust fallbacks
            common_name = tags.get("name") or tags.get("description") or f"Stop {stop_id}"
            street_name = tags.get("addr:street") or tags.get("highway") or "Public Transport Network"
            town_name = tags.get("addr:city") or tags.get("addr:town") or tags.get("operator") or "Portugal Region"

            parsed_rows.append({
                "stop_id": stop_id,
                "common_name": common_name,
                "street_name": street_name,
                "town_name": town_name,
                "lat": float(lat),
                "lon": float(lon)
            })

        df = pd.DataFrame(parsed_rows)

        if df.empty:
            print("ERROR: No rows passed extraction.")
            return

        # Drop duplicates based on identical coordinates
        df = df.drop_duplicates(subset=["lat", "lon"]).reset_index(drop=True)

        # 3. Structural Output Construction
        print("Step 3: Building structured CSV...")
        processed_df = pd.DataFrame()

        # Generate PT Index Number
        processed_df['Index Number'] = [f"PT{i}" for i in range(len(df))]
        processed_df['Stop Number'] = df['stop_id']
        processed_df['Common Stop Name'] = df['common_name']
        processed_df['Street Name'] = df['street_name']
        processed_df['Town Name'] = df['town_name']

        # Precise coordinate rounding to 4 decimal places
        processed_df['Latitude'] = df['lat'].round(4)
        processed_df['Longitude'] = df['lon'].round(4)

        # 4. Save to Disk
        processed_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nSUCCESS! Exported clean file to '{output_file}' with {len(processed_df)} entries.")

    except Exception as e:
        print(f"CRITICAL PROCESSING ERROR: {e}")

if __name__ == "__main__":
    download_and_process_pt_stops()