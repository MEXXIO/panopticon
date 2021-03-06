#!/usr/bin/env python3

'''
Panopticon by Megumi Sonoda
Copyright 2016, Megumi Sonoda
This file is licensed under the BSD 3-clause License
'''

# Imports from stdlib
import asyncio
import base64
from datetime import datetime
from datetime import timezone
import os
import re
import signal
import sys

# Imports from dependencies
import discord
from discord.enums import ChannelType

# Import configuration
from config import (
    TOKEN, BOT_ACCOUNT,
    USE_LOCALTIME, LOG_DIR,
    MAX_MESSAGES, AWAY_STATUS
)

print('panopticon starting')

# Import IGNORE_SERVER separately, which was added later and might not exist in
#   config.py for some users. This is to prevent the script from crashing.
IGNORE_SERVERS = []
try:
    from config import IGNORE_SERVERS
except ImportError:
    pass
except:
    raise


# This sanitizes an input string to remove characters that aren't valid
#   in filenames. There are a lot of other bad filenames that can appear,
#   but given the predictable nature of our input in this application,
#   they aren't handled here.
def clean_filename(string):
    return re.sub(r'[/\\:*?"<>|\x00-\x1f]', '', string)


# This builds the relative file path & filename to log to,
#   based on the channel type of the message.
# It is affixed to the log directory set in config.py
def make_filename(message):
    if message.edited_timestamp:
        time = message.edited_timestamp
    else:
        time = message.timestamp
    timestamp = time.strftime('%F')
    if message.channel.type == ChannelType.text:
        return "{}/{}-{}/#{}-{}/{}.log".format(
            LOG_DIR,
            clean_filename(message.server.name),
            message.server.id,
            clean_filename(message.channel.name),
            message.channel.id,
            timestamp
        )
    elif message.channel.type == ChannelType.private:
        return "{}/DM/{}-{}/{}.log".format(
            LOG_DIR,
            clean_filename(message.channel.user.name),
            message.channel.user.id,
            timestamp
        )
    elif message.channel.type == ChannelType.group:
        return "{}/DM/{}-{}/{}.log".format(
            LOG_DIR,
            clean_filename(message.channel.name),
            message.channel.id,
            timestamp
        )


# Uses a Message object to build a very pretty string.
# Format:
#   (messageid) [21:30:00] <user#0000> hello world
# Message ID will be base64-encoded since it becomes shorter that way.
# If the message was edited, prefix messageid with E:
#   and use the edited timestamp and not the original.
def make_message(message):
    # Wrap the message ID in brackets, and prefix E: if the message was edited.
    # Also, base64-encode the message ID, because it's shorter.
    #   This uses less space on disk, and is easier to read in console.
    message_id = '[E:' if message.edited_timestamp else '['
    message_id += "{}]".format(base64.b64encode(
        int(message.id).to_bytes(8, byteorder='little')
    ).decode('utf-8'))

    # Get the datetime from the message
    # If necessary, tell the naive datetime object it's in UTC
    #   and convert to localtime
    if message.edited_timestamp:
        time = message.edited_timestamp
    else:
        time = message.timestamp
    if USE_LOCALTIME:
        time = time.replace(tzinfo=timezone.utc).astimezone(tz=None)

    # Convert the datetime to a string in [21:30:00] format
    timestamp = time.strftime('[%H:%M:%S]')

    # Get the author's name, in distinct form, and wrap it
    # in IRC-style brackets
    author = "<{}#{}>".format(
        message.author.name,
        message.author.discriminator
    )

    # Get the message content. Use `.clean_content` to
    #   substitute mentions for a nicer format
    content = message.clean_content.replace('\n', '\n(newline) ')

    # If the message has attachments, grab their URLs
    # attachments = '\n(attach) '.join(
    #     [attachment['url'] for attachment in message.attachments]
    # )
    attachments = ''
    if message.attachments:
        for attach in message.attachments:
            attachments += '\n(attach) {0[url]}'.format(attach)

    # Use all of this to return as one string
    return("{} {} {} {} {}".format(
        message_id,
        timestamp,
        author,
        content,
        attachments
    ))


# Append to file, creating path if necessary
def write(filename, string):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'a', encoding='utf8') as file:
        file.write(string + "\n") 
        #print(string, file=file)


# Create client object
client = discord.Client()


# Register event handlers
# On message send
@client.event
async def on_message(message):
    if message.server and message.server.id in IGNORE_SERVERS:
        return
    filename = make_filename(message)
    string = make_message(message)
    write(filename, string)


# On message edit
# Note from discord.py documentation:
#   If the message is not found in the Client.messages cache, then these
#   events will not be called. This happens if the message is too old
#   or the client is participating in high traffic servers.
# Through testing, messages from before the current client session also do
#   not fire the event.
@client.event
async def on_message_edit(_, message):
    if message.server and message.server.id in IGNORE_SERVERS:
        return
    filename = make_filename(message)
    string = make_message(message)
    write(filename, string)


# On ready
# Typically, a bot, self-bot or otherwise, has an always-green/'active'
#   status indicator. This provides the option to change the status when the
#   actual user goes offline or away.
@client.event
async def on_ready():
    await client.change_presence(status=AWAY_STATUS)


# Run client
client.run(TOKEN, bot=BOT_ACCOUNT, max_messages=MAX_MESSAGES)
