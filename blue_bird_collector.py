# @charset "utf-8"
import os
import sys
import json
import time
import requests
import urllib.parse
import pandas as pd
import datetime
import hashlib
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

#====================================================================
# 現在日時を取得
#====================================================================
def get_now_str():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9), 'JST'))
    return now.strftime('%Y/%m/%d(%a) %H:%M:%S')

#====================================================================
# api endpointを作成する
#====================================================================
def create_endpoint_url(method):
    return 'https://api.twitter.com/2' + method

#====================================================================
# usernames一覧のuserdataを取得
#====================================================================
def create_users_endpoint_url(usernames):
    unames = 'usernames=' + ','.join(usernames)
    user_fields = 'user.fields=description,created_at,profile_image_url'
    return create_endpoint_url(f'/users/by?{unames}&{user_fields}')

#====================================================================
# 指定userのtweet一覧を取得
#====================================================================
def create_user_tweets_endpoint_url(id):
    max_results = 'max_results=100'
    tweet_fields = 'tweet.fields=attachments,text,id'
    expansions = 'expansions=attachments.media_keys'
    media_fields = 'media.fields=media_key,type,url,variants'
    return create_endpoint_url(f'/users/{id}/tweets?{max_results}&{tweet_fields}&{expansions}&{media_fields}')

#====================================================================
# connect to endpoint
#====================================================================
def connect_to_endpoint_by_bearer(url, params={}):
    print("################# BY_BARER")
    print(url)
    print(params)
    def bearer_oauth(r):
        r.headers["Authorization"] = f"Bearer {os.getenv('TWITTER_BEARER_TOKEN')}"
        r.headers["User-Agent"] = "v2UserTweetsPython"
        return r

    while True:
        response = requests.request("GET", url, auth=bearer_oauth, params=params)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code in (420, 429):
                print('RATE LIMIT WAIT')
                print('RESPONSE', response.json())
                print('LIMIT', response.headers['x-rate-limit-limit'])
                print('REMAINING', response.headers['x-rate-limit-remaining'])
                print('RESET WAIT', int(response.headers['x-rate-limit-reset']) - int(time.time()))
                dt_jst_aware = datetime.datetime.fromtimestamp(int(response.headers['x-rate-limit-reset']),
                                                               datetime.timezone(datetime.timedelta(hours=9)))
                print(dt_jst_aware)
                time.sleep(int(response.headers['x-rate-limit-reset']) - int(time.time()) + 60)
                continue
            print('ERROR :', e)
            print('RESPONSE', response.json())
            sys.exit()
        except requests.exceptions.ConnectTimeout:
            print('requests.exceptions.ConnectTimeout:')
            print('RESPONSE', response.json())
            time.sleep(10)
            continue
        except OtherException as e:
            print('OTHER ERROR :', e)
            print('RESPONSE', response.json())
            sys.exit()
        else:
            print('200:')
            #print('RESPONSE', response.json())
            print('LIMIT', response.headers['x-rate-limit-limit'])
            print('REMAINING', response.headers['x-rate-limit-remaining'])
            print('RESET WAIT', int(response.headers['x-rate-limit-reset']) - int(time.time()))
            return response.json()

#====================================================================
# 指定ユーザの画像、動画を取得する
#====================================================================
def get_twitter_media(data, loop_index, header, cookie):
    print(f'#{loop_index}:{data.username}********************************************************************')
    time.sleep(1)
    username = data.username

    # フォルダが無ければ作成
    outdir = f"{os.getenv('TWITTER_OUTDIR')}/{username}"
    if (not os.path.isdir(outdir)) and (not os.path.exists(outdir)):
        print(f'{outdir}を作成')
        os.makedirs(outdir)

    # tweet一覧を取得
    params = {}
    media_urls = {}
    tweet_id_list = []
    while True:
        res = connect_to_endpoint_by_bearer(create_user_tweets_endpoint_url(data.id), params)
        video = {}
        photo = {}
        # 先にメディアの情報を集める
        if 'includes' in res and 'media' in res['includes']:
            for m in res['includes']['media']:
                if m['type'] == 'video' or m['type'] == 'animated_gif':
                    video[m['media_key']] = sorted(m['variants'], key=lambda x:'bit_rate' in x and -x['bit_rate'])[0]
                else:
                    photo[m['media_key']] = m['url']
        # ツイートを処理する
        if 'data' in res:
            for tweet in res['data']:
                tid = tweet['id']
                if int(tid) <= int(data.max):
                    break
                tweet_id_list.append(tid) #+ meta のnewとoldとるほうが優しい
                tweet_fname = f'{outdir}/{tid.zfill(19)}_tweet.txt'
                if not os.path.isfile(tweet_fname):
                    with open(tweet_fname, 'w', encoding='UTF-8') as f:
                        f.write(tweet['text'])
                if 'attachments' not in tweet:
                    continue
                if 'media_keys' not in tweet['attachments']:
                    continue
                mcnt = 0
                pcnt = 0
                for mkey in tweet['attachments']['media_keys']:
                    # 動画を保存
                    if mkey in video:
                        #+ほんとはcontent_typeを見たほうが良い
                        video_fname = f'{outdir}/{tid.zfill(19)}_mov_{str(mcnt).zfill(3)}.mp4'
                        mcnt += 1
                        if not os.path.isfile(video_fname):
                            vr = requests.get(video[mkey]['url'], headers=header, cookies=cookie)
                            if vr.status_code == 200:
                                with open(video_fname, 'wb') as f:
                                    f.write(vr.content)
                    # 画像を保存
                    if mkey in photo:
                        ext = photo[mkey].split('.')[-1]
                        photo_fname = f'{outdir}/{tid.zfill(19)}_img_{str(pcnt).zfill(3)}.{ext}'
                        pcnt += 1
                        if not os.path.isfile(photo_fname):
                            pr = requests.get(f'{photo[mkey]}:orig', headers=header, cookies=cookie)
                            if pr.status_code == 200:
                                with open(photo_fname, 'wb') as f:
                                    f.write(pr.content)
        # 続きがあるか確認
        if 'meta' in res:
            if 'newest_id' in res['meta'] and int(res['meta']['newest_id']) <= int(data.max):
                break
            if 'next_token' in res['meta']:
                params = { 'pagination_token':res['meta']['next_token'] }
                continue
        break
    
    # プロフィール画像取得
    if data.profile_image_url != "":
        pimg_url = data.profile_image_url.replace('_normal', '')
        pimg_parse = urllib.parse.urlparse(pimg_url)
        pimg_name = outdir + '/' + pimg_parse.path.replace('/', '_')
        if not os.path.isfile(pimg_name):
            res = requests.get(pimg_url, headers=header, cookies=cookie)
            if res.status_code == 200:
                with open(pimg_name, 'wb') as f:
                    f.write(res.content)

    # プロフ保存
    hash = ''
    if data.description != "":
        prof_path = f"{outdir}/_profile.txt"
        hash = hashlib.sha256(data.description.encode()).hexdigest()
        if not os.path.isfile(prof_path) or data.desc_hash != hash:
            with open(prof_path, 'a', encoding='UTF-8') as f:
                f.write("-------------------------------------\n")
                f.write(get_now_str() + "\n")
                f.write(data.description + "\n")

    return tweet_id_list, hash

#********************************************************************
def main():
    start_time = get_now_str()
    load_dotenv()

    # 設定ファイル読み込み
    args = sys.argv
    if len(args) != 3:
        print('設定ファイルを引数に指定してください')
        sys.exit()
    twitter_csv = args[1]
    twitter_result_csv = args[2]

    # データフレーム作成
    df = pd.DataFrame(index=[], columns=['username','id','name','max','description','desc_hash','profile_image_url','created','modified'])

    # twitter_csvから取得対象を読み込む
    twitter_csv_df = pd.read_csv(twitter_csv, header=None, names=['username'])

    # twitter_result_csvが存在すればdfに読み込む
    if os.path.isfile(twitter_result_csv):
        df = pd.read_csv(twitter_result_csv, dtype={'max':str, 'id':str, 'description':str, 'desc_hash':str,'profile_image_url':str})
        if 'description' not in df.columns:
            df['description'] = ''
        if 'desc_hash' not in df.columns:
            df['desc_hash'] = ''
        if 'profile_image_url' not in df.columns:
            df['profile_image_url'] = ''

    # dfにマージする
    df = pd.merge(twitter_csv_df, df, on='username', how='outer')

    # 全ユーザの更新情報のチェック
    ulist = df['username'].to_list()
    err_user_name = []
    for i in range(0, len(ulist), 100):
        res = connect_to_endpoint_by_bearer(create_users_endpoint_url(ulist[i: i+100]))
        for data in res['data']:
            df.loc[df['username'] == data['username'], 'id'] = data['id']
            df.loc[df['username'] == data['username'], 'name'] = data['name']
            if 'description' in data:
                df.loc[df['username'] == data['username'], 'description'] = data['name'] + "\n" + data['description']
            if 'profile_image_url' in data:
                df.loc[df['username'] == data['username'], 'profile_image_url'] = data['profile_image_url']
        # エラーがあったユーザを記憶する（たまに存在していてもエラーになる場合がある）
        if 'errors' in res:
            print("--------USER-ERRORS")
            print(res['errors'])
            for err in res['errors']:
                err_user_name.append(err['value'])
    # エラーになったユーザーを記録する
    with open(f'{twitter_csv}.err', 'w') as f:
        f.write("\n".join(err_user_name))

    # NAデータを埋め込む
    df = df.fillna({'created':get_now_str(), 'modified':get_now_str() })
    df = df.fillna({'max':'0'})

    df = df.drop_duplicates(subset='username')
    desc = df.describe()
    #df = df.sample(frac = 1, ignore_index=True) # 毎回ランダムな順番に処理するならコメントアウト

    # cookieがあれば読み込む
    # editthiscookieなどで取得する
    cookie = {}
    if os.path.isfile('cookie.json'):
        with open('cookie.json') as f:
            for c in json.load(f):
                cookie[c['name']] = c['value']
    header = { 'User-Agent': 'v2UserTweetsPython' }

    # リストのユーザーを巡回して画像・動画を取得
    loop_count = 0
    for row in df.itertuples():
        loop_count += 1
        # エラーリストに載っている場合はスキップする
        if row.username in err_user_name:
            continue
        tweet_list, desc_hash = get_twitter_media(row, loop_count-1, header, cookie)
        if len(tweet_list) > 0:
            df.loc[df['username'] == row.username, 'modified'] = get_now_str()
            if int(row.max) < int(max(tweet_list)):
                df.loc[df['username'] == row.username, 'max'] = str(max(tweet_list))
        df.loc[df['username'] == row.username, 'desc_hash'] = desc_hash
        # 未取得は1回につき1アカウントづつ実行する
        if int(row.max) == 0 and len(tweet_list) > 0:
            break;

    # 設定ファイルを書き戻す
    df.to_csv(twitter_result_csv, index=False)

    end_time = get_now_str()
    print('')
    print(start_time)
    print(end_time)

if __name__ == '__main__':
    main()
