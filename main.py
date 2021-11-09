from discord_components import ComponentsBot

import admin
import cfg
import constant
import discord
import distribute
import source
import re
import user
import util
import view
import json

bot = ComponentsBot('?')
util.start_logger()

admin_tokens = None
discord_token = None
with open('local_settings.json') as infile:
    data = json.load(infile)
    admin_tokens = data['admin_token']
    discord_token = data['discord_token']


@bot.event
async def on_ready():
    initialize_global_vars()

    print('CF Senior EPGP start')

@bot.event
async def on_voice_state_update(member, before, after):
    #https://stackoverflow.com/questions/61918331/discord-js-join-leave-voice-channel-notification-in-text-channel?rq=1
    newChannel = after.channel
    if (newChannel is not None and newChannel.id == constant.raid_channel):
        print(member.name + ' joined server')
        # raider_dict can be empty only the raid is not started.
        if (len(cfg.raider_dict) == 0):
            return
        for name, raider in cfg.raider_dict.items():
            if raider.author_id == member.id:
                raider.in_raid = True
                msg = await member.send(
                     '欢迎参加本次Raid %s' % (name),
                     components=view.user_view_component(False),
                     embed=view.my_pr_embed(member.id))
                cfg.raid_user_msg.update({member.id: msg})

                #Update roster section of admin view
                await cfg.admin_msg.edit(embed=view.loot_admin_embed())

                util.log_msg('%s 加入Raid' % name)
    elif (newChannel is None or newChannel.id != constant.raid_channel):
        print(member.name + " left server")
        # raider_dict can be empty only the raid is not started.
        if (len(cfg.raider_dict) == 0):
            return
        for name, raider in cfg.raider_dict.items():
            if raider.author_id == member.id:
                raider.in_raid = False
                util.log_msg('%s 离开Raid' % name)

@bot.event
async def on_button_click(interaction):
    custom_id = interaction.custom_id

    if (custom_id == None):
        return
    elif (custom_id.startswith('user')):
        await on_user_view_click(interaction)
    elif (custom_id.startswith('loot')):
        await on_loot_view_click(interaction)
    elif (custom_id.startswith('reward')):
        await on_reward_click(interaction)


@bot.event
async def on_message(message):
    if (type(message.channel) is not discord.DMChannel):
        return

    if (message.author == bot.user):
        return

    if (match_keywork(constant.admin_reg, message)):
        await on_admin_message(message)
    elif (match_keywork(constant.dis_reg, message)):
        await on_distribution_message(message)
    else:
        await on_user_message(message)


async def on_user_message(message):
    if (cfg.admin == None):
        await message.channel.send('管理员还未开始本次Raid, 请稍后再试')
        return

    if (match_keywork(constant.login_reg, message)):
        await user.member_login(message)
    else:
        await message.author.send('''
      指令              用途
    Login 游戏ID      进入Raid

    Admin指令（只有管理员可以使用）
    Admin|a 具体指令 (-h for help)
    Distribute|d 具体指令 (-h for help)
    Raid|r 具体指令 (-h for help)
    ''')


async def on_user_view_click(interaction):
    author = interaction.user
    custom_id = interaction.custom_id

    if (custom_id == (constant.user_raid_pr_list_id + cfg.stamp)):
        original_msg = cfg.raid_user_msg[author.id]
        await original_msg.edit(embed=view.raid_pr_embed())
        await interaction.respond(
            type=constant.update_message_button_response_type)
    elif (custom_id == (constant.user_my_pr_id + cfg.stamp)):
        original_msg = cfg.raid_user_msg[author.id]
        await original_msg.edit(embed=view.my_pr_embed(author.id))
        await interaction.respond(
            type=constant.update_message_button_response_type)
    elif (custom_id == (constant.user_main_spec_id + cfg.stamp)):
        cfg.main_spec.append(author.id)

        original_msg = cfg.raid_user_msg[author.id]
        await original_msg.edit(components=view.user_view_component(
            enable_loot_button=False))
        await interaction.respond(
            type=constant.update_message_button_response_type)

    elif (custom_id == (constant.user_off_spec_id + cfg.stamp)):
        cfg.off_spec.append(author.id)

        original_msg = cfg.raid_user_msg[author.id]
        await original_msg.edit(components=view.user_view_component(
            enable_loot_button=False))
        await interaction.respond(
            type=constant.update_message_button_response_type)


async def on_admin_message(message):
    if (str(message.author) not in admin_tokens):
        await message.channel.send('您不是管理员')
        return

    if (match_keywork(constant.start_new_raid_reg, message)):
        await admin.start_new_raid(message)
    elif (match_keywork(constant.add_new_member_reg, message)):
        await admin.add_new_member(message)
    elif (match_keywork(constant.decay_reg, message)):
        await admin.decay(message)
    elif (match_keywork(constant.adjust_reg, message)):
        await admin.adjust(message)
    elif (match_keywork(constant.gbid_reg, message)):
        await admin.gbid(message)
    elif (match_keywork(constant.standby_reg, message)):
        await admin.standby(message)
    elif (match_keywork(constant.recover_reg, message)):
        await admin.recover_raid(message, bot)
    elif (match_keywork(constant.sync_from_discord_channel, message)):
        await admin.sync_from_discord_channel(message, bot)
    elif (match_keywork(constant.sync_epgp_from_gsheet_to_json, message)):
        await source.sync_epgp_from_gsheet_to_json(message)
    elif (match_keywork(constant.sync_loot_from_gsheet_to_json, message)):
        await source.sync_loot_from_gsheet_to_json(message)
    elif (match_keywork(constant.load_epgp_from_json_to_memory, message)):
        source.load_epgp_from_json_to_memory()
    elif (match_keywork(constant.load_loot_from_json_to_memory, message)):
        source.load_loot_from_json_to_memory()
    elif (match_keywork(constant.dump_epgp_from_memory_to_json, message)):
        await source.dump_epgp_from_memory_to_json(message)
    elif (match_keywork(constant.dump_loot_from_memory_to_json, message)):
        source.dump_loot_from_memory_to_json()
    else:
        await message.author.send('''
        指令              用途
      Admin|a start      开始raid
      Admin|a add -id    游戏ID [-ep XX] [-gp XX] 添加新的游戏ID到DB
      Admin|a decay      衰减DB中所有的EP/GP
      Admin|a adjust -id 游戏ID [-ep XX] [-gp XX] [-r 原因] 修改游戏ID的EP/GP
      Admin|a gbid -id 游戏ID [-l XX] [-g XX] 记录gbid交易
      Admin|a g2js pr    Gsheet中导入所有人的pr信息到epgp.json文件
      Admin|a g2js loot  Gsheet中导入所有loot信息到loot.json文件
      Admin|a js2m pr    epgp.json导入epgp对象
      Admin|a js2m loot  loot.json导入loot对象
      Admin|a (write|w)  epgp对象导入epgp.json
      Admin|a m2js loot  loot对象导入loot.json
      ''')


async def on_distribution_message(message):
    if (str(message.author) not in admin_tokens):
        await message.channel.send('您不是管理员')
        return

    if (cfg.admin == None):
        await admin.start_new_raid(message)
        return

    if (match_keywork(constant.announcement_reg, message)):
        await distribute.announcement(message)


async def on_loot_view_click(interaction):
    custom_id = interaction.custom_id
    if (custom_id == (constant.loot_off_spec_confirm_id + cfg.stamp)):
        await distribute.confirm(constant.gp_off_spec_factor)
        await interaction.respond(
            type=constant.update_message_button_response_type)
    elif (custom_id == (constant.loot_main_spec_confirm_id + cfg.stamp)):
        await distribute.confirm(constant.gp_main_spec_factor)
        await interaction.respond(
            type=constant.update_message_button_response_type)
    elif (custom_id == (constant.loot_cancel_id + cfg.stamp)):
        await distribute.cancel()
        await interaction.respond(
            type=constant.update_message_button_response_type)


async def on_reward_click(interaction):
    custom_id = interaction.custom_id

    match = re.fullmatch("reward (20|150|200)%s" % (cfg.stamp), custom_id)
    if (match):
        ep = int(match[1])

        eligible_raiders = []
        for raider in cfg.raider_dict.values():
            if ((raider.in_raid == True) & (raider.stand_by == False)):
                util.set_ep(raider.ID, ep + util.get_ep(raider.ID))
                eligible_raiders.append(raider.ID)

        await interaction.respond(
            type=constant.update_message_button_response_type)
        util.log_msg('%sEP奖励给%s' % (ep, eligible_raiders))


def match_keywork(keyword, message):
    return re.fullmatch(keyword, message.content, re.IGNORECASE)


def initialize_global_vars():
    cfg.admin = None
    cfg.raider_dict = {}
    cfg.loot_dict = {}
    cfg.stamp = ''

    cfg.main_spec = None
    cfg.off_spec = None
    cfg.current_winner = None
    cfg.current_loot = None
    cfg.loot_message = None

    cfg.raid_user_msg = {}
    cfg.admin_msg = None


bot.run(discord_token)