from hikari import GatewayBot, GuildMessageCreateEvent, Intents, Embed, EmbedField, PermissionOverwriteType, Permissions, PermissionOverwrite, Snowflake
import simplejson as json
import time
from sqlitedict import SqliteDict
from dataclasses import dataclass
import asyncio

# Data Setup
staff_team_role_id = 1054537894410321970
owner_role_id = 1054537575592902816
member_role_id = 1054538517562277959
ticket_archive_channel_id = 1054559991547301999
sql = SqliteDict('data.db', autocommit=True)
token = 'MTA1NDU1MDEzMjk4Njc1NzIyMA.G5UOT4.uMaFRBHRkxfp7YywO9c1UVNHbyiNpOxiEeisfg'
client = GatewayBot(token, intents=Intents.ALL)


@dataclass(frozen=True)
class Ticket:
    id: int
    owner: int
    channel: int
    creation_time: str
    archive: dict = None


# Define some Hikari events and listen for messages.
@client.listen()
async def on_message_create(event: GuildMessageCreateEvent):
    if event.is_bot or not event.content:
        return

    role_id = event.member.role_ids

    if event.content == '!ping':
        if not staff_team_role_id in role_id or not owner_role_id in role_id:
            embed = Embed(
                title='**You do not have permission!**',
                description='You do not have permission to use this command.',
                color=0xff0000
            )
            await event.message.respond(embed=embed)
            return

        await event.message.respond('Pong!')

# Bot Setup
if __name__ == '__main__':
    client.run()
