import os
import re
import tweepy
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

twitterAPIKey = st.secrets["twitterAPIKey"]
twitterAPIKeySecret = st.secrets["twitterAPIKeySecret"]
twitterAccessToken = st.secrets["twitterAccessToken"]
twitterAccessTokenSecret = st.secrets["twitterAccessTokenSecret"]

auth = tweepy.OAuthHandler(twitterAPIKey, twitterAPIKeySecret)
auth.set_access_token(twitterAccessToken, twitterAccessTokenSecret)
api = tweepy.API(auth)

def get_jwave_tweets(start_date, end_date):
    tweets = []
    for tweet in tweepy.Cursor(api.user_timeline, screen_name="@jwave", tweet_mode="extended", since=start_date, until=end_date).items():
        result = re.search(r'「(.+)」\s+(.+)\s+(\d{2}:\d{2})', tweet.full_text)
        if result:
            song = result.group(1)
            artist = result.group(2)
            tweets.append(f'"{song}" {artist} {result.group(3)}')
        else:
            continue
    return tweets

@st.cache_data
def parse_jwave_tweets(tweets):
    data = []
    pattern = r'"(.+)"\s+(.+)\s+(.+)'
    for tweet in tweets:
        result = re.search(pattern, tweet)
        if result:
            song = result.group(1)
            artist = result.group(2)
            time_str = result.group(3)
            try:
                time = datetime.strptime(time_str, "%H:%M")
            except ValueError:
                continue
            data.append({"song": song, "artist": artist, "time": time})
    return pd.DataFrame(data)

@st.cache_data
def create_youtube_search_link(song, artist):  # 追加: 関数定義
    youtube_query = f"{song} {artist} official video"
    youtube_query = youtube_query.replace(" ", "+")
    youtube_link = f"https://www.youtube.com/results?search_query={youtube_query}&force_navigate=1"
    return youtube_link

@st.cache_data
def search_youtube_video(song, artist):
    youtube = build('youtube', 'v3', developerKey=youtubeAPIKey)
    request = youtube.search().list(
        part='id',
        q=f'{song} {artist} MV',
        type='video'
    )
    response = request.execute()
    if 'items' in response:
        return response['items']
    else:
        return None

st.set_page_config(layout="wide")
st.sidebar.title("データ取得期間の指定")

start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
start_date = st.sidebar.text_input("開始日 (YYYYMMDD形式):", start_date)
end_date = datetime.now().strftime("%Y%m%d")
end_date = st.sidebar.text_input("終了日 (YYYYMMDD形式):", end_date)

if st.sidebar.button("データ取得"):
    with st.spinner('データを取得しています...'):
        tweets = get_jwave_tweets(start_date, end_date)
        df = parse_jwave_tweets(tweets)
        df["song_artist"] = df["song"] + " - " + df["artist"]

        song_count = df["song_artist"].value_counts().head(30)
        song_rank = []
        for i in range(len(song_count)):
            song_rank.append(i+1)

        st.subheader("J-WAVE楽曲オンエア数ランキング")

        for i in range(len(song_count)):
            song_artist = song_count.index[i]
            count = song_count[song_artist]
            song, artist = song_artist.split(" - ")
            # 以下変更: search_youtube_video を使用せず、create_youtube_search_link を使用
            url = create_youtube_search_link(song, artist)
            st.write(f"{i+1}. [{song}]({url}) - {artist} ({count}回再生)")

        df_artist_rank = pd.DataFrame({'Rank': song_rank, 'Artist': df['artist'].value_counts().head(30).index, 'Count': df['artist'].value_counts().head(30).values})
        st.subheader("アーティストオンエア数ランキング")
        st.table(df_artist_rank[['Rank', 'Artist', 'Count']])