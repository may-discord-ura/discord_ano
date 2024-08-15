import os
import discord
import json
import random
import re
import time
import string
import datetime
from discord.ui import Modal, Button, View, TextInput  #モーダル関連
from collections import defaultdict, deque

from discord import app_commands
from discord.ext import commands, tasks
from datetime import timedelta

# インテントの生成
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# botの定義
bot = commands.Bot(intents=intents, command_prefix="$", max_messages=10000)
tree = bot.tree

# コマンドの実行タイミングを記録する連中（連投制限用）
last_executed = {}
last_executed['temp'] = 0

# 設定ファイルのパス
CONFIG_FILE = 'config.json'
CHANNEL_LIST = "channels.json"
ANONYM_LIST = 'anolist.json'

# 真名看破処理が既に行われたメッセージIDのセット
processed_messages_special = set()

### 関数定義
# 設定を読み込む
def load_config(file):
    with open(file, 'r') as f:
        return json.load(f)

# 設定を書き込む
def save_config(config, file):
    with open(file, 'w') as f:
        json.dump(config, f, indent=4)

# id生成用の関数
def get_random_string(length: int) -> str:
    random_source = string.ascii_letters + string.digits
    random_string = ''.join(
        (random.choice(random_source) for i in range(length)))
    return random_string


# idをjsonに格納・読み出しする関数
def reload_ids(user_id):
    global member_data
    with open("ids.json", "r", encoding="utf-8") as json_file:
        member_data = json.load(json_file)
    check_date()
    if str(user_id) not in member_data:
        new_data = {
            "tid":
            get_random_string(8),
            "color":
            random.choice((0x66cdaa, 0x7cfc00, 0xffd700, 0xc0c0c0,0xba55d3))  #水色、緑、橙、灰、紫
        }
        member_data[user_id] = new_data
    # jsonを書き込んで読み込み直す
    with open("ids.json", "w", encoding="utf-8") as json_file:
        json.dump(member_data, json_file, ensure_ascii=False, indent=4)
    with open("ids.json", "r", encoding="utf-8") as json_file:
        member_data = json.load(json_file)


def check_date():
    global member_data
    global day_count
    day_now = datetime.date.today().day
    if day_now != day_count:
        day_count = day_now
        config["day_count"] = day_count
        save_config(config, CONFIG_FILE)
        member_data = {}

#ano本体
async def ano_post(本文: str,user_id: int,id表示: bool,添付ファイル: discord.Attachment = None,interaction: discord.Interaction = None,resmode: bool = False,message:discord.Message =None,channelid:int =None,attachment_file:discord.File =None,attachment_file_log:discord.File =None):
    #連投制限
    current_time = time.time()
    if user_id in last_executed and current_time - last_executed[user_id] < 15 and interaction:
        await interaction.response.send_message(
            content=f"連続で実行できません。ちょっと（5秒くらい）待ってね。書き込もうとした内容→　{本文}",
            ephemeral=True)
        return

    #ID生成
    reload_ids(user_id)

    # 通し番号を更新してファイルに保存
    global command_count
    command_count += 1
    config["command_count"] = command_count
    save_config(config, CONFIG_FILE)

    ###本番送信部分###
    # ID表示チェック
    if id表示:
        emb_id = "ID:" + member_data[str(user_id)]["tid"]
    else:
        emb_id = ""

    # 添付ファイルをFile形式に変更
    if 添付ファイル:
        attachment_file = await 添付ファイル.to_file()
        attachment_file_log = await 添付ファイル.to_file()
    
    # 半角スペースx2を改行に変換
    本文 = 本文.replace("  ", "\n")

    # 埋め込みを作成
    ano_embed = discord.Embed(
        title='',
        description=f"{本文}\n ",  #0624
        color=member_data[str(user_id)]["color"]  # 色を指定 (青色)0x3498db
    )

    # 埋め込みに情報を追加
    if resmode is True:
        ano_embed.set_footer(text=f'とくめいさん#{str(command_count)} 返信版')
    else:
        ano_embed.set_footer(text=f'とくめいさん#{str(command_count)} {emb_id}')

    # 実行ユーザー宛に成功メッセージを送信
    if interaction:
        await interaction.response.send_message(ephemeral=True,content="書き込み成功！このメッセージは自動で消えます",delete_after=3)

    # 添付ファイルが画像の場合、埋め込み内に画像を表示
    url_without_query =""
    if attachment_file:
        url_without_query = re.sub(r'\?.*$', '', attachment_file.filename.lower())
        if url_without_query.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            ano_embed.set_image(url=f"attachment://{attachment_file.filename}")
        else:
            ano_embed.add_field(name="添付ファイル", value=attachment_file.filename, inline=False)

    # コマンドを実行したチャンネルにメッセージを送信
    if channelid:
        message_channel = bot.get_channel(channelid)
    else:
        message_channel = interaction.channel
        
    if resmode is True: # 返信版
        message = await message.reply(embed=ano_embed)
    elif attachment_file:
        message = await message_channel.send(embed=ano_embed, file=attachment_file)
    else: # 添付ファイルのない通常投稿
        message = await message_channel.send(embed=ano_embed)

    # 開示用のリスト生成
    global anonyms
    anonyms[message.id] = [command_count, user_id]
    save_config(anonyms, ANONYM_LIST)
    
    ###ログ送信部分###
    # コマンドを実行したチャンネルorスレッドを取得
    # 自動変換の場合とそうでない場合
    try:
        thread_id = interaction.channel_id
        thread_name = interaction.channel.name
        username = interaction.user.name
    except Exception:
        thread_id = channelid
        thread_name = message_channel.name
        username = bot.get_user(user_id)

    # ログ保存用チャンネルにメッセージを送信
    log_channel = bot.get_channel(LOG_CHANNEL_ID[0])
    if log_channel:
        log_message = (
            f"**名前:** {username}<@{user_id}>\n"  #0624
            f"**チャンネル:**{thread_name}<#{thread_id}>\n"
            f"**内容:** {本文}"  #0624
            f"　[jump]({message.jump_url})"  #0624
        )
        log_embed = discord.Embed(
            title='Anonymous実行ログ#' + str(command_count),
            description=log_message,
            color=0x3498db  # 色を指定 (青色)
        )

        #添付ファイルの有無で分岐
        if attachment_file_log:
            url_without_query = re.sub(r'\?.*$', '', attachment_file_log.filename.lower())
            if url_without_query.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                log_embed.set_image(url=f"attachment://{attachment_file_log.filename}")
            else:
                log_embed.add_field(name="添付ファイル", value=attachment_file_log.filename, inline=False)
                
        if attachment_file_log:
            await log_channel.send(embed=log_embed, file=attachment_file_log)
        else:
            await log_channel.send(embed=log_embed)
        
    else:
        print(f"チャンネルID {LOG_CHANNEL_ID[0]} が見つかりませんでした")

    # コマンドの実行タイミングを記録
    last_executed[user_id] = current_time


### -----on_readyゾーン------
# discordと接続した時に呼ばれる
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}.")
    await tree.sync()
    print("Synced slash commands.")


    """設定をファイルから読み込む"""
    global command_count
    global day_count
    global config
    global PREDEFINED_NAME
    global TARGET_CHANNEL_ID,AUTODELETE_CHANNEL_ID, LOG_CHANNEL_ID, SPEED_CHANNEL_ID, FORUM_ALERT_CHANNEL_ID, BOTCOMMAND_ALERT_CHANNEL_ID,DELETE_LOG_CHANNEL_ID
    global BOT_AUTODELETE_ID, ANO_CHANGE_CHANNEL_ID, EARTHQUAKE_CHANNEL_ID
    global server_timezone
    global is_enabled_threadstop, is_enabled_react, is_enabled_futaba
    global is_enabled_channelspeed, is_enabled_msgdellog #ログ関係
    global is_enabled_onmessage_bot, is_enabled_onmessage_temp
    global is_enabled_anochange, is_enabled_earthquake
    global last_eq_id
    global anonyms
    command_count = 0  # コマンド実行回数をカウントするための変数
    if os.path.exists(CONFIG_FILE):
        # 初期設定の読み込み
        config = load_config(CONFIG_FILE)
        if config.get('server_timezone', "UTC") == "JST":# タイムゾーンを定義
            JST = datetime.timezone(timedelta(hours=+9), 'JST')
            server_timezone = JST
        else:
            UTC = datetime.timezone(timedelta(hours=+0), 'UTC')
            server_timezone = UTC
        command_count = config.get('command_count', 0)
        day_count = config.get('day_count', 0)
        is_enabled_threadstop = config.get('is_enabled_threadstop', False)
        is_enabled_react = config.get('is_enabled_react', False)
        is_enabled_futaba = config.get('is_enabled_futaba', False)
        is_enabled_channelspeed = config.get('is_enabled_channelspeed', False)
        is_enabled_onmessage_bot = config.get('is_enabled_onmessage_bot',False)
        is_enabled_onmessage_temp = config.get('is_enabled_onmessage_temp',False)
        is_enabled_msgdellog = config.get('is_enabled_msgdellog', False)
        is_enabled_anochange = config.get('is_enabled_anochange', False)
        is_enabled_earthquake= config.get('is_enabled_earthquake', False)
        PREDEFINED_NAME = config.get('PREDEFINED_NAME', "としあき")
        last_eq_id = config.get('last_eq_id', "0")


    if os.path.exists(CHANNEL_LIST):
        channels = load_config(CHANNEL_LIST)
        LOG_CHANNEL_ID = channels.get('ログ保存先チャンネル', [])
        
    if os.path.exists(AUTODELETE_LIST):
        autodelete_config = load_config(AUTODELETE_LIST)

    # 匿名投稿の開示用リスト読み込み
    if os.path.exists(ANONYM_LIST):
        anonyms = load_config(ANONYM_LIST)
    else:
        anonyms = {}

### -----スラッシュコマンド------
# ヘルプコマンド
@tree.command(name="help", description="botの機能や使い方を表示するよ")
async def help(interaction: discord.Interaction):

    embed = discord.Embed(title="ヘルプ",
        description="",
        color=discord.Color.blue())

    embed_title ="/ano（スラッシュコマンド）"
    embed_value ="名前を隠してメッセージを送信するコマンドです。発言に返信されても通知が来ないので注意\n"
    embed_value+="- __オプション__\n"
    embed_value+=" - 本文：メッセージの本文を入力（半角スペース2連続で改行になります）\n"
    embed_value+=" - id表示：Trueにするとidが出ます（毎日0時更新）\n"
    embed_value+=" - 添付ファイル：ファイルを添付する時に指定してね\n"
    embed_value+="※オプションを全部省略すると本文入力用の画面が出ます\n"
    embed_value+="※添付ファイルを指定して本文を省略するとｷﾀｰAA略になります"
    embed_value+="※添付ファイルは一回の投稿で一つまでです"
    embed.add_field(name=embed_title,value=embed_value,inline=False)

    embed_title ="👀自動匿名変換（機能）"
    embed_value ="特定のチャンネルでメッセージが送信されると、自動で名前を隠して（`/ano`状態で）再送信します\n"
    embed_value+="現在、覆面座談会スレがこの機能の対象です"
    embed_value+="※複数ファイルを添付した場合、__最初のファイルのみ__が添付されます（2番目以降のファイルは消えます）"
    embed.add_field(name=embed_title,value=embed_value,inline=False)

    await interaction.response.send_message(embed=embed,ephemeral=True)

#その場でBOTに発言させる匿名発言用コマンド
@tree.command(name="ano", description="発言したチャンネル内にメッセージ内容を発言します。ファイル添付・ID表示可")
@app_commands.describe(本文="送信するメッセージ内容。半角スペースを2連続で入力すると改行に変わります",添付ファイル="省略可",id表示="TRUEにするとランダムな英数字8文字が出る（0時更新）")
async def ano(interaction: discord.Interaction,本文: str = "",id表示: bool = False,添付ファイル: discord.Attachment = None):

    if interaction.guild is None:
        await interaction.response.send_message("DM内では使えないよ",ephemeral=True)
        return
    
    ###事前チェック部分###
    #本文と添付ファイルがどっちもない場合はモーダルを表示
    if 本文 == "":
        if 添付ファイル is None:
            await interaction.response.send_modal(
                ReplyModal(channel=interaction.channel))
            return
        else:
            本文 = "ｷﾀ━━━━━(ﾟ∀ﾟ)━━━━━!!"

    user_id = interaction.user.id
    await ano_post(本文, user_id, id表示, 添付ファイル, interaction, False)


#匿名レス機能の本体
class ReplyModal(Modal):
    def __init__(self, message=None, channel=None):
        if message:
            title = "とくめいさんに返信してもらう"
            label = "返信レス本文"
            desc = "ここに返信レス内容を入力する（ファイル添付はできません）"
            self.resmode = True
            self.message = message
        else:
            title = "とくめいさんに発言してもらう"
            label = "レス本文"
            desc = "ここにレス本文を入力する（ファイル添付はできません）"
            self.resmode = False
            self.message = None
            self.channel = channel
        super().__init__(title=title)
        self.add_item(
            TextInput(label=label,
                      placeholder=desc,
                      style=discord.TextStyle.paragraph,
                      required=True))

    async def on_submit(self, interaction: discord.Interaction):
        reply_content = self.children[0].value
        ###事前チェック部分###
        #本文がない場合はエラー
        if reply_content is None:
            await interaction.response.send_message(content="！エラー！本文を入力してね",
                                                    ephemeral=True)
            return

        user_id = interaction.user.id
        await ano_post(reply_content, user_id, False, None, interaction,self.resmode, self.message)


### -----コンテキストメニュー------
# 匿名でレスするコンテキストメニュー
@tree.context_menu(name="とくめいさんにレスさせる")
async def ano_reply(interaction: discord.Interaction,message: discord.Message):
    await interaction.response.send_modal(ReplyModal(message))
  

### --------------on_reaction_addコーナー-------------- ###
# delが溜まるとタイムアウト
@bot.event
async def on_reaction_add(reaction, user):
    global anonyms
    if reaction.message.author == bot.user:  #botへのリアクションのみ反応。匿名発言にDELが20個溜まったら真名看破
        if str(reaction.emoji) == '<:DEL:1247440603244003438>' and reaction.count == 21 and reaction.message.id not in processed_messages_special:
            try:
                post_num = anonyms[reaction.message.id][0]
                user_id = anonyms[reaction.message.id][1]
                processed_messages_special.add(reaction.message.id)
                del_embed = discord.Embed(
                    title="【真名看破】",
                    description=f"### 占いの結果、__とくめいさん#{post_num}__の発言者は<@{user_id}>だったようです",
                    color=0xff0000  # 色を指定 (赤)
                )
                await reaction.message.reply(embed=del_embed, silent=True)
            except Exception:
                return

### --------------on_messageコーナー-------------- ###
@bot.event
async def on_message(message):
    # 指定チャンネルの発言を匿名変換
    if is_enabled_anochange:
        if not message.author.bot and message.channel.id in ANO_CHANGE_CHANNEL_ID:  # 発言者がbotでない場合、指定のチャンネル以外で実行
            # 添付ファイルを取得
            attachment_file = None
            attachment_file_log = None
            if message.attachments:
                attachment = message.attachments[0]
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as response:
                        if response.status == 200:
                            data = await response.read()
                            # ファイル名をクリーンアップ
                            filename = re.sub(r'[^\w\.\-]', '_', attachment.filename)
                            # バイナリデータをメモリに保存
                            attachment_file = discord.File(io.BytesIO(data), filename=filename)
                            attachment_file_log = discord.File(io.BytesIO(data), filename=filename)# ログに添付する用

            # 返信かどうかを確認
            res_message = None
            resmode = False
            if message.reference:
                res_message = await message.channel.fetch_message(message.reference.message_id)
                resmode = True
            
            await ano_post(message.content, message.author.id, False, None, None, resmode, res_message,message.channel.id,attachment_file,attachment_file_log)
            await message.delete()
