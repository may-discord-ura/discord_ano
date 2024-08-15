# discord_ano
discordで匿名発言するbot

## 機能
- botに代理でメッセージを投稿させる（スラッシュコマンド`ano`）
- botに代理でメッセージを返信させる（コンテキストメニュー`とくめいさんにレスさせる`）
- 指定したチャンネルの発言を自動でbotからの投稿に置き換える
- 実行ログの出力機能

## 準備
### discord側の準備
- 開発者ポータルからbotを作成する
  - トークンを確保
  - `MESSAGE CONTENT INTENT`をオンにする
  - `Administrator`権限を付与するか、`Attach Files`,`MAnage Messages`,`Send Messages`,`Send Messages in Threads`,`View Channels`を付与
### サーバーの設定
- 環境変数`TOKEN`にbotのトークンを入れておいてください
  - 面倒な場合は`main.py`最終行の`"TOKEN"`に直接トークンを入れる
### botの設定
- `指定したチャンネルの発言を自動でbotからの投稿に置き換える`機能を使用する場合、channel.json内の"匿名変換対象チャンネル"にチャンネルIDを入れてください

## 実行
run main.py

## 備考
匿名発言をさせたくない場合、discordの`連携サービス`内で権限設定をする
