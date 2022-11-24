# 推しのTwitterのツイートや画像や動画をローカルに収集したいよね

ローカルに収集して自由に見返したり、むふむふしたりしたいよね。  
という欲求をTwitter APIでかなえたものです。

## <span style="color:red">免責事項&注意事項</span>

自分の環境・使い方で動けばいいや。で作っているので検証、デバッグが圧倒的に足りていないです。  
本プロジェクトを利用した、または利用できなかった、その他いかなる場合において一切の保障は行いません。  
自己の責任のもとでご利用ください。

## 使い方

1. 仮想環境名venvで仮想環境作成する。違う名称の場合はblue_bird_collector.batの中身を修正する
1. pip install -r requirements.txtする
1. twitter.csv.sampleに収集したい推しのアカウント名を列記してtwitter.csvにリネームする
1. cookieありで画像や動画を取得したい場合はcookie.json.sampleにcookieの情報を記載してcookie.jsonにリネームする  
cookie情報はThisEditCookieなどでとってこよう。
1. 適当にググってTwitter API v2を使えるようにする
1. できればさらに適当にググって、Elevatedまで昇格する
1. .env.sampleに収集保存先のフォルダとTwitter API v2のベアラートークンを記載する
1. blue_bird_collector.batを起動する
1. 保存先と指定したフォルダにアカウント毎のフォルダが作成されてツイートや画像や動画などが保存されているはず
1. twitter_result.csvとかtwitter.csv.errとかのファイルもできますが気にしない

## 注意

連続実行したらAPIのRATE LIMITが速攻で来そうなので、1回の実行につき新規で収集するのは1アカウントづつにしています。  
タスクスケジューラーで15分おきに実行するなどいい感じに工夫してください。  
  
以上です。
