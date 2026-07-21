import os
import requests
import pandas as pd

def download_and_process_fr_stops(output_file="france_transit_stops.csv"):
    temp_raw_file = "raw_france_stops.csv"
    dataset_api_url = "https://www.data.gouv.fr/api/1/datasets/651d2ece3af956b8dd0d7648/"

    # 1. Dynamically resolve latest CSV resource URL and stream download
    try:
        print("Step 1: Fetching dataset metadata from data.gouv.fr API...")
        api_res = requests.get(dataset_api_url, timeout=30)
        api_res.raise_for_status()
        dataset_meta = api_res.json()

        # Find the latest CSV resource URL
        csv_url = None
        for res in dataset_meta.get("resources", []):
            if res.get("format", "").lower() == "csv":
                csv_url = res.get("latest") or res.get("url")
                break

        if not csv_url:
            print("CRITICAL ERROR: Could not resolve CSV download URL from API.")
            return

        print(f"-> Streaming live data from: {csv_url}")
        with requests.get(csv_url, stream=True, timeout=120) as response:
            response.raise_for_status()
            with open(temp_raw_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
        print(f"-> Download complete. Size: {os.path.getsize(temp_raw_file) / (1024*1024):.2f} MB")

    except Exception as e:
        print(f"CRITICAL NETWORK ERROR: {e}")
        return

    # 2. Data Cleaning and Gap Prevention
    try:
        print("\nStep 2: Processing French stop data and removing gaps...")
        raw_data = pd.read_csv(temp_raw_file, low_memory=False, encoding='utf-8-sig', on_bad_lines='skip')

        # Normalize column headers to lowercase
        raw_data.columns = raw_data.columns.str.lower()

        # Identify latitude/longitude columns
        lat_col = 'stop_lat' if 'stop_lat' in raw_data.columns else 'latitude'
        lon_col = 'stop_lon' if 'stop_lon' in raw_data.columns else 'longitude'
        name_col = 'stop_name' if 'stop_name' in raw_data.columns else 'commonname'

        # Filter missing coordinates and names
        filtered_df = raw_data.dropna(subset=[lat_col, lon_col, name_col]).copy()

        # Ensure valid numeric coordinates
        filtered_df[lat_col] = pd.to_numeric(filtered_df[lat_col], errors='coerce')
        filtered_df[lon_col] = pd.to_numeric(filtered_df[lon_col], errors='coerce')
        filtered_df = filtered_df.dropna(subset=[lat_col, lon_col])

        # Fill text field defaults
        street_val = filtered_df['addr:street'] if 'addr:street' in filtered_df.columns else 'Public Transport Network'
        town_val = filtered_df['agency_name'] if 'agency_name' in filtered_df.columns else 'France Region'

        filtered_df['street'] = street_val if isinstance(street_val, pd.Series) else 'Public Transport Network'
        filtered_df['town'] = town_val if isinstance(town_val, pd.Series) else 'France Region'

        filtered_df['street'] = filtered_df['street'].fillna('Public Transport Network')
        filtered_df['town'] = filtered_df['town'].fillna('France Region')

        # Reset index to eliminate row gaps
        filtered_df = filtered_df.reset_index(drop=True)

        if filtered_df.empty:
            print("ERROR: No rows passed the filtering criteria.")
            return

        # 3. Output Schema Construction
        print("Step 3: Constructing structured CSV...")
        processed_df = pd.DataFrame()

        processed_df['Index Number'] = [f"FR{i}" for i in range(len(filtered_df))]
        
        if 'stop_id' in filtered_df.columns:
            processed_df['Stop Number'] = filtered_df['stop_id'].astype(str)
        else:
            processed_df['Stop Number'] = [f"{i+1:03d}" for i in range(len(filtered_df))]

        processed_df['Common Stop Name'] = filtered_df[name_col].astype(str)
        processed_df['Street Name'] = filtered_df['street'].astype(str)
        processed_df['Town Name'] = filtered_df['town'].astype(str)

        # Coordinate precision: 4 decimal places
        processed_df['Latitude'] = filtered_df[lat_col].round(4)
        processed_df['Longitude'] = filtered_df[lon_col].round(4)

        # 4. Save to Disk
        processed_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nSUCCESS! Clean file exported to '{output_file}' with {len(processed_df)} entries.")

    except Exception as e:
        print(f"CRITICAL PROCESSING ERROR: {e}")
    finally:
        if os.path.exists(temp_raw_file):
            os.remove(temp_raw_file)

if __name__ == "__main__":
    download_and_process_fr_stops()