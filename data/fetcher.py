import requests
import pandas as pd


def fetch_market_data(api_config,interval,date_in="live",time_in=None):

    # if date is null or empty, set to "live"
    if not date_in or date_in.strip() == "":
        date_in = "live"
    
    response = requests.get(
        api_config["url"],
        params=api_config["params"] | {"date": date_in} | {"interval": "30"},
        timeout=10
    )
    response.raise_for_status()
    # if response status code is not 200, raise exception
    if response.status_code != 200:
        raise Exception(f"API request failed with status code {response.status_code}")

    df = pd.DataFrame(response.json())

    for col in ["spx", "spxExpectedMove", "spxOTMBids", "vix"]:
        df[col] = df[col].astype(float)

    df['dateTime'] = pd.to_datetime(df['dateTime'], unit='s').dt.tz_localize('UTC').dt.tz_convert('America/New_York')

    # set dateTime as index and sort by dateTime
    df.set_index('dateTime', inplace=True)
    df.sort_index(inplace=True)

    df_m = df[
        (df.index.minute % interval == 0) &
        (df.index.second == 0)
    ]

    # if time_in is provided, filter dataframe to only include rows before time_in on date_in
    if time_in:
        time_filter = pd.to_datetime(f"{date_in} {time_in}").tz_localize('America/New_York')
        df_m = df_m[df_m.index <= time_filter]

    
    return df_m
