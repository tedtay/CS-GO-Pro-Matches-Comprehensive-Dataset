import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
from datetime import datetime
import re
import undetected_chromedriver
import argparse
import traceback
from google.cloud import storage
import gcsfs
import chromedriver_binary
import os
import lxml

BUCKET_NAME = "web_scraping_hltv"
PROJECT_NAME = ""
DATASET_NAME = ""
TABLE_NAME = ""


os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="./festive-tiger-392211-2fb4fcc2785b.json"

def get_player_stats(bs):
    try:
        t1_player_stats = []
        table_body = bs.select("body > div.bgPadding > div.widthControl > div:nth-child(2) > div.contentCol > div.stats-section.stats-match > div:nth-child(13) > table")[0]
        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            t1_player_stats.append([ele for ele in cols if ele]) # Get rid of empty values
        t1_player_stats = t1_player_stats[1:]

        t2_player_stats = []
        table_body = bs.select("body > div.bgPadding > div.widthControl > div:nth-child(2) > div.contentCol > div.stats-section.stats-match > div:nth-child(32) > table")[0]
        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            t2_player_stats.append([ele for ele in cols if ele]) # Get rid of empty values
        t2_player_stats = t2_player_stats[1:]
    except:
        try:
            t1_player_stats = []
            table_body = bs.select("body > div.bgPadding > div.widthControl > div:nth-child(2) > div.contentCol > div.stats-section.stats-match > div:nth-child(16) > table")[0]
            rows = table_body.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                cols = [ele.text.strip() for ele in cols]
                t1_player_stats.append([ele for ele in cols if ele]) # Get rid of empty values
            t1_player_stats = t1_player_stats[1:]

            t2_player_stats = []
            table_body = bs.select("body > div.bgPadding > div.widthControl > div:nth-child(2) > div.contentCol > div.stats-section.stats-match > div:nth-child(35) > table")[0]
            rows = table_body.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                cols = [ele.text.strip() for ele in cols]
                t2_player_stats.append([ele for ele in cols if ele]) # Get rid of empty values
            t2_player_stats = t2_player_stats[1:]
        except:
            pass
        
    return [t1_player_stats, t2_player_stats]

def get_rounds_breakdown(bs):
    return bs.find_all(class_='match-info-row')[0].find_all('div')[0].text

def get_first_kills(bs):
    return bs.find_all(class_='match-info-row')[2].find_all('div')[0].text

def get_clutches_won(bs):
    return bs.find_all(class_='match-info-row')[3].find_all('div')[0].text

def write_to_cloud_storage(data, bucket_name: str, path_name: str, ):
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(path_name)
    blob.upload_from_string(data)
    

def scrape(start_from_row: int = 0):
    options = undetected_chromedriver.ChromeOptions()
    options.add_argument("headless")
    options.add_argument("incognito")
    driver = undetected_chromedriver.Chrome(options=options, executable_path = '/usr/bin/chromedriver')
    
    print("---- Passed ----")
    # ----- changed to download from gcp
    df_all_games = pd.read_csv(f'gs://{BUCKET_NAME}/cloud_function_data/historic_games_list.csv')

    game_data = []
    exception_data = []
    
    # scrapes all data using above methods
    # stores in temp dict which is then appended to a list of other dicts
    for row_num in range(start_from_row,len(df_all_games['game_link'])):
        thisgame_link = df_all_games['game_link'].iloc[row_num]
        try:
            # can remove options to run in foreground
            driver.get("https://www.hltv.org"+thisgame_link)
            bs = BeautifulSoup(driver.page_source, "lxml")

            rounds_breakdown = get_rounds_breakdown(bs)
            first_kills = get_first_kills(bs)
            clutches_won = get_clutches_won(bs)
            player_stats = get_player_stats(bs)

            thisgame = {
                "team1_half1_t": int(re.findall('\(.*?\)', re.findall('\(.*?\)', rounds_breakdown)[0])[0].replace('(', '').replace(')', '').split(":")[0]),
                "team2_half1_ct": int(re.findall('\(.*?\)', re.findall('\(.*?\)', rounds_breakdown)[0])[0].replace('(', '').replace(')', '').split(":")[1]),
                "team1_half2_ct": int(re.findall('\(.*?\)', re.findall('\(.*?\)', rounds_breakdown)[1])[0].replace('(', '').replace(')', '').split(":")[0]),
                "team1_half2_t": int(re.findall('\(.*?\)', re.findall('\(.*?\)', rounds_breakdown)[1])[0].replace('(', '').replace(')', '').split(":")[1]),
                "team1_first_kills": int(first_kills.replace('(', '').replace(')', '').split(":")[0]), 
                "team2_first_kills": int(first_kills.replace('(', '').replace(')', '').split(":")[1]), 
                "team1_clutches_won": int(clutches_won.replace('(', '').replace(')', '').split(":")[0]),
                "team2_clutches_won": int(clutches_won.replace('(', '').replace(')', '').split(":")[1]),
                "team1_p1_name": player_stats[0][0][0],
                "team1_p1_khs": player_stats[0][0][1],
                "team1_p1_assists": player_stats[0][0][2],
                "team1_p1_deaths": player_stats[0][0][3],
                "team1_p1_kast": player_stats[0][0][4],
                "team1_p1_kddiff": player_stats[0][0][5],
                "team1_p1_adr": player_stats[0][0][6],
                "team1_p1_fkdiff": player_stats[0][0][7],
                "team1_p1_game_rating": player_stats[0][0][8],
                "team1_p2_name": player_stats[0][1][0],
                "team1_p2_khs": player_stats[0][1][1],
                "team1_p2_assists": player_stats[0][1][2],
                "team1_p2_deaths": player_stats[0][1][3],
                "team1_p2_kast": player_stats[0][1][4],
                "team1_p2_kddiff": player_stats[0][1][5],
                "team1_p2_adr": player_stats[0][1][6],
                "team1_p2_fkdiff": player_stats[0][1][7],
                "team1_p2_game_rating": player_stats[0][1][8],
                "team1_p3_name": player_stats[0][2][0],
                "team1_p3_khs": player_stats[0][2][1],
                "team1_p3_assists": player_stats[0][2][2],
                "team1_p3_deaths": player_stats[0][2][3],
                "team1_p3_kast": player_stats[0][2][4],
                "team1_p3_kddiff": player_stats[0][2][5],
                "team1_p3_adr": player_stats[0][2][6],
                "team1_p3_fkdiff": player_stats[0][2][7],
                "team1_p3_game_rating": player_stats[0][2][8],
                "team1_p4_name": player_stats[0][3][0],
                "team1_p4_khs": player_stats[0][3][1],
                "team1_p4_assists": player_stats[0][3][2],
                "team1_p4_deaths": player_stats[0][3][3],
                "team1_p4_kast": player_stats[0][3][4],
                "team1_p4_kddiff": player_stats[0][3][5],
                "team1_p4_adr": player_stats[0][3][6],
                "team1_p4_fkdiff": player_stats[0][3][7],
                "team1_p4_game_rating": player_stats[0][3][8],
                "team1_p5_name": player_stats[0][4][0],
                "team1_p5_khs": player_stats[0][4][1],
                "team1_p5_assists": player_stats[0][4][2],
                "team1_p5_deaths": player_stats[0][4][3],
                "team1_p5_kast": player_stats[0][4][4],
                "team1_p5_kddiff": player_stats[0][4][5],
                "team1_p5_adr": player_stats[0][4][6],
                "team1_p5_fkdiff": player_stats[0][4][7],
                "team1_p5_game_rating": player_stats[0][4][8],
                "team2_p1_name": player_stats[1][0][0],
                "team2_p1_khs": player_stats[1][0][1],
                "team2_p1_assists": player_stats[1][0][2],
                "team2_p1_deaths": player_stats[1][0][3],
                "team2_p1_kast": player_stats[1][0][4],
                "team2_p1_kddiff": player_stats[1][0][5],
                "team2_p1_adr": player_stats[1][0][6],
                "team2_p1_fkdiff": player_stats[1][0][7],
                "team2_p1_game_rating": player_stats[1][0][8],
                "team2_p2_name": player_stats[1][1][0],
                "team2_p2_khs": player_stats[1][1][1],
                "team2_p2_assists": player_stats[1][1][2],
                "team2_p2_deaths": player_stats[1][1][3],
                "team2_p2_kast": player_stats[1][1][4],
                "team2_p2_kddiff": player_stats[1][1][5],
                "team2_p2_adr": player_stats[1][1][6],
                "team2_p2_fkdiff": player_stats[1][1][7],
                "team2_p2_game_rating": player_stats[1][1][8],
                "team2_p3_name": player_stats[1][2][0],
                "team2_p3_khs": player_stats[1][2][1],
                "team2_p3_assists": player_stats[1][2][2],
                "team2_p3_deaths": player_stats[1][2][3],
                "team2_p3_kast": player_stats[1][2][4],
                "team2_p3_kddiff": player_stats[1][2][5],
                "team2_p3_adr": player_stats[1][2][6],
                "team2_p3_fkdiff": player_stats[1][2][7],
                "team2_p3_game_rating": player_stats[1][2][8],
                "team2_p4_name": player_stats[1][3][0],
                "team2_p4_khs": player_stats[1][3][1],
                "team2_p4_assists": player_stats[1][3][2],
                "team2_p4_deaths": player_stats[1][3][3],
                "team2_p4_kast": player_stats[1][3][4],
                "team2_p4_kddiff": player_stats[1][3][5],
                "team2_p4_adr": player_stats[1][3][6],
                "team2_p4_fkdiff": player_stats[1][3][7],
                "team2_p4_game_rating": player_stats[1][3][8],
                "team2_p5_name": player_stats[1][4][0],
                "team2_p5_khs": player_stats[1][4][1],
                "team2_p5_assists": player_stats[1][4][2],
                "team2_p5_deaths": player_stats[1][4][3],
                "team2_p5_kast": player_stats[1][4][4],
                "team2_p5_kddiff": player_stats[1][4][5],
                "team2_p5_adr": player_stats[1][4][6],
                "team2_p5_fkdiff": player_stats[1][4][7],
                "team2_p5_game_rating": player_stats[1][4][8],
                "game_link": thisgame_link,
                "collected_timestamp": datetime.now()
            }
            game_data.append(thisgame)

        except Exception as ex:
            # create exception dict so can see when failed last
            thisexception = {
                "row_num": row_num,
                "timestamp": datetime.now(),
                "game_link": thisgame_link,
                "next_game_link": df_all_games.iloc[row_num+1]['game_link'],
                "exception": ex,
                "stack_trace": traceback.format_exc()
            }
            exception_data.append(thisexception)
            write_to_cloud_storage(
                data = pd.DataFrame(exception_data).to_csv(index=False), 
                bucket_name = BUCKET_NAME,
                path_name= f"cloud_function_data/exception_data.csv"
            )
            print(f"Logged Exception No.{len(exception_data)} @ row_num - {row_num}")
        
        # every nth row game_data
        if(row_num%10 == 0):
            write_to_cloud_storage(
                data = pd.DataFrame(game_data).to_csv(index=False), 
                bucket_name = BUCKET_NAME,
                path_name = f"cloud_function_data/game_data.csv"
            )
            
            driver.quit()
            options = undetected_chromedriver.ChromeOptions()
            options.add_argument("headless")
            options.add_argument("incognito")
           # options.add_argument("sandbox")
            driver = undetected_chromedriver.Chrome(options=options)
            print(f"Save game_data @ row_num - {row_num} -->  {datetime.now()}")
            


if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Scrape hltv game data')
    parser.add_argument('-sfr', '--start_from_row', type=int, help='add start_from_row')
    args = parser.parse_args()
    
    scrape(args.start_from_row)
