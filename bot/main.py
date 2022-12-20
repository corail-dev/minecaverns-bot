from hikari import GatewayBot, GuildMessageCreateEvent, Intents, Embed, EmbedField, PermissionOverwriteType, Permissions, PermissionOverwrite, Snowflake
import simplejson as json
import time
from sqlitedict import SqliteDict
from dataclasses import dataclass
import asyncio
from jsonpickle import encode, decode
from commands import ping, ticket_create, ticket_close, values_sql, ticket_counter

# Data Setup
sql = SqliteDict('data.db', autocommit=True)
token = 'MTA1NDU1MDEzMjk4Njc1NzIyMA.G5UOT4.uMaFRBHRkxfp7YywO9c1UVNHbyiNpOxiEeisfg'
client = GatewayBot(token, intents=Intents.ALL)


# Define some Hikari events and listen for messages.
@client.listen()
async def on_message_create(event: GuildMessageCreateEvent):
    if event.is_bot or not event.content:
        return

    content = event.content

    if content == '!ping':
        await ping(client=client, event=event)

    if content == '!ticket create':
        await ticket_create(client=client, event=event)

    if content == '!ticket close':
        await ticket_close(client=client, event=event)

# Bot Setup
if __name__ == '__main__':

    # Create an example Ticket object and pickle it, print it, then unpickle it and print it again.
    if values_sql.__contains__('ticket_counter'):
        ticket_counter = values_sql['ticket_counter']

    client.run()
