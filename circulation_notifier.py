#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import urllib.parse  # urlencode
import configparser
import requests
import os
import json

# カレントディレクトリを移動
dirPath = os.path.dirname(os.path.abspath(__file__))
os.chdir(dirPath)

# 過去回覧チェック用のテキスト。ファイルある事前提。極小のDBとかでやりたい
path_w = './src/existing_notification.txt'

"""
事前処理
・設定ファイルから情報を読み込む
　Basic認証情報/ログイン情報/アクセスURI/クッキーを返すログインURI/SlackのWEBHOOK_URI
・inputタグの情報
"""
# iniから設定ファイル読み込み
config = configparser.ConfigParser()
config.read('./src/config.ini')

# アクセスするURI
targetUri = config['accessUri']['targetUri']
targetLoginUri = config['accessUri']['targetLoginUri']

# ログイン情報
ba_user = config['basicAuth']['ba_user']
ba_pass = config['basicAuth']['ba_pass']
username = config['loginDate']['username']
password = config['loginDate']['password']

# input情報
payload = {
    "cmd": "certify",
    "nexturl": "dneo.cgi",
    "svuid": "",
    "starttab": "0",
    "UserID": username,
    "_word": password,
    "svlid": "1"
}

"""
主処理開始
postリクエスト ～ベーシック認証とログイン情報のせ～
ログイン後のクッキー情報を取得する
"""
# セッションを開始
session = requests.session()

# URLをエンコード
params = urllib.parse.urlencode(payload)

# postリクエストにBasic認証アカウントとINPUTタグ情報を載せて送信
r = session.post(url=targetLoginUri, data=params, auth=(ba_user, ba_pass))
r.raise_for_status() # エラーならここで例外を発生させる

# 送信結果が知りたい場合には記載
print(r.status_code)
print(r.text)
print("======================ベーシック認証後========================")

"""
ログイン用のクッキー情報を取得したので、
リクエストヘッダに入力してgetリクエストを送信する。
dnzSid = rssid, dnzToken = STOKEN, dnzSv = dnzSv
"""
# 取得したcookieを整形してリクエストヘッダに挿入
getCookieJson = r.text
jsonGetCookieDict = json.loads(getCookieJson)

dnzSid = format(jsonGetCookieDict['rssid'])
dnzToken = format(jsonGetCookieDict['STOKEN'])
dnzSv = format(jsonGetCookieDict['dnzSv'])

postCookie = 'dnzHashcmd=fin; dnzInfo=139; dnzPtab=S; dnzSid=' + dnzSid + '; dnzToken=' + dnzToken + '; dnzSv=' + dnzSv + '; m2kps=; '

# 追加するヘッダー情報作成(ここ未整理なのでもうちょっと何か)
headers = {
    'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    'Cookie': postCookie,
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'
}

# get用にBasic認証情報とユーザ情報と作成したヘッダを追加してページ取得
session.auth = (ba_user, ba_pass)
session.data = params
session.headers.update(headers)
r = session.get(url=targetUri)

# 取得したHTMLを格納
html = r.text
print("======================  DOM要素取得後  ========================")

"""
取得したDOM要素を整形して、テキスト比較して、slackへ送信
"""
# 既存の回覧一覧テキストを読み込み
checkExistingNotifications = open(path_w, "r")

# パーサー
#soup = BeautifulSoup(html, "html.parser")
soup = BeautifulSoup(html, "lxml")

# 投稿日時とタイトルの一覧に分解
dates = soup.select('td[class^="portal-listitem-datetime"]')
titles = soup.select('a[data-hashcmd^="creportindex"]')

# リスト投入用の変数
circulationContentList = [""]

# 投稿日時とタイトルの一覧を整形してループ
for date, title in zip(dates, titles):
    # HTMLから取得した回覧リスト
    circulationContent = date.string + title.string

    # マッチカウント用初期化
    count = 0

    # 通知済みの回覧と確認
    for content in checkExistingNotifications:

        # 今回の一覧とマッチ判定
        matchFlagWithList = circulationContent in content

        # マッチしたらカウント増やして抜ける
        if matchFlagWithList is True:
            count += 1
            break

    # カウントが0で通知済み回覧と一致がなければslackへ通知
    if count is 0:
        print("新しい回覧があります：" + circulationContent)

        WEB_HOOK_URI = config['slackWebHook']['WEB_HOOK_URI']
        requests.post(WEB_HOOK_URI, data = json.dumps({
            'text': u'新しい回覧があります：' + circulationContent,  #通知内容
            'link_names': 1,  #名前をリンク化
        }))

    # 出力用の既存一覧に追加
    circulationContentList.append(circulationContent)

# テキストに書き出す
with open(path_w, mode='w') as w:
    w.writelines('\n'.join(circulationContentList))


