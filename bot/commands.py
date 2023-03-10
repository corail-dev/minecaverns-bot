import asyncio

from hikari import GatewayBot, GuildChannel, GuildMessageCreateEvent, Embed, EmbedField, PermissionOverwriteType, \
    Permissions, PermissionOverwrite, Snowflake, File
from sqlitedict import SqliteDict
from jsonpickle import encode, decode
from dataclasses import dataclass
import pastebinpy as pbp
import random
import time

tickets_sql = SqliteDict('tickets.db', autocommit=True)
values_sql = SqliteDict('values.db', autocommit=True)
archived_tickets_sql = SqliteDict('archived_tickets.db', autocommit=True)
ticket_counter = 0
tickets = {}
archived_tickets = {}
staff_team_role_id = 1054537894410321970
owner_role_id = 1054537575592902816
member_role_id = 1054538517562277959
ticket_archive_channel_id = 1054559991547301999
pastebin_api_key = 'oMdNCtLHo-zzWyGyZo-pxoAsDfACiDWG'
main_guild = 1054537386584985702
waiting_on_message = []
selected_channel = {}

# Fetch all string values in tickets_sql and decode them into Ticket objects.
for key, value in tickets_sql.items():
    tickets[key] = decode(value.encode('utf-8'))

# Fetch all string values in archived_tickets_sql and decode them into Ticket objects.
for key, value in archived_tickets_sql.items():
    archived_tickets[key] = decode(value.encode('utf-8'))

if values_sql.__contains__('ticket_counter'):
    ticket_counter = values_sql['ticket_counter']


@dataclass(frozen=True)
class TicketMessage:
    content: str
    author: str
    author_id: int
    timestamp: str


@dataclass(frozen=False)
class Ticket:
    id: int
    owner: int
    channel: int
    creation_time: str
    archive: dict = None


@dataclass(frozen=True)
class ArchivedTicket:
    id: int
    owner: int
    channel: int
    creation_time: str
    archive: dict = None


def generate_random_string(length: int):
    # Generate a random string of a given length.
    letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


async def suggest(client: GatewayBot, event: GuildMessageCreateEvent):
    if event.is_bot or not event.content:
        return

    role_id = event.member.role_ids

    suggestion_array = event.content.split(' ', 1)
    if len(suggestion_array) < 2:
        embed = Embed(
            title='**Invalid Arguments**',
            description='You must provide a suggestion.',
            color=0xff0000
        )
        await event.message.respond(embed=embed)
        return

    suggestion = suggestion_array[1]

    embed = Embed(
        title='**Suggestion**',
        description=f'{suggestion}',
        color=0x00ff00
    )
    embed.add_field('Suggested by', f'<@{event.member.id}>', inline=False)
    embed.add_field('Suggested in', f'<#{event.channel_id}>', inline=True)
    message = await client.rest.create_message(1054816621866258462, embed=embed)

    # Add :arrow_up_small: and :arrow_down_small: reactions to the message.
    await asyncio.sleep(0.1)
    await client.rest.add_reaction(channel=message.channel_id, message=message, emoji='????')
    await asyncio.sleep(0.1)
    await client.rest.add_reaction(channel=message.channel_id, message=message, emoji='????')

    global main_guild
    discord_message_url = f'https://discord.com/channels/{main_guild}/{message.channel_id}/{message.id}'

    # Make it into an embed
    embed = Embed(
        title='**Suggestion created!**',
        description=f'Your suggestion has been sent in the <#1054816621866258462> channel\nYou can view your suggestion here: [Click to view your suggestion]({discord_message_url})',
        color=0x00ff00
    )
    # Send it to the suggestions channel
    await client.rest.create_message(event.channel_id, embed=embed)


async def announcement_listener(client: GatewayBot, event: GuildMessageCreateEvent):
    if event.is_bot or not event.content:
        return

    role_id = event.member.role_ids

    if event.content.startswith('!announce'):
        if not staff_team_role_id in role_id or not owner_role_id in role_id:
            embed = Embed(
                title='**You do not have permission!**',
                description='You do not have permission to use this command.',
                color=0xff0000
            )
            await event.message.respond(embed=embed)
            return

    if not selected_channel.__contains__(event.member.id) and event.member.id in waiting_on_message:
        message = event.content
        if not message.isdigit():
            embed = Embed(
                title='**Invalid Arguments**',
                description='You must provide a valid channel ID.',
                color=0xff0000
            )
            await event.message.respond(embed=embed)
            return

        selected_channel[event.member.id] = int(message)
        embed = Embed(
            title='**Channel Selected**',
            description=f'You have selected <#{message}> as the announcement channel.\nPlease send the announcement message in this channel.',
            color=0x00ff00
        )
        await event.message.respond(embed=embed)
        return

    # Get the member's profile picture URL and username
    profile_picture_url = event.member.avatar_url
    username = event.member.username

    if event.member.id in waiting_on_message:
        embed = Embed(
            title='**Announcement**',
            description=f'{event.content}',
            color=0x00ff00
        )
        embed.set_author(name=username, url="https://www.minecaverns.com/", icon=profile_picture_url)
        message = await client.rest.create_message(selected_channel[event.member.id], embed=embed)
        del selected_channel[event.member.id]
        await event.message.respond('Announcement sent!')
        waiting_on_message.remove(event.member.id)


async def chat_listener(client: GatewayBot, event: GuildMessageCreateEvent):
    # Whenever someone sends a message in a ticket channel, detect what ticket it is and add it to the archive.
    channel_id = event.channel_id
    ticket = tickets.get(channel_id)

    if not ticket:
        return

    content = event.content
    author = event.member.username
    author_id = event.member.id
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    ticket_message = TicketMessage(
        content=content,
        author=author,
        author_id=author_id,
        timestamp=timestamp
    )

    if not ticket.archive:
        ticket.archive = {}

    ticket.archive[timestamp] = ticket_message
    tickets_sql[channel_id] = encode(ticket)
    tickets[channel_id] = ticket

    await asyncio.sleep(0.1)


async def ping(client: GatewayBot, event: GuildMessageCreateEvent):
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


async def ticket_create(client: GatewayBot, event: GuildMessageCreateEvent):
    if event.is_bot or not event.content:
        return

    role_id = event.member.role_ids

    if not staff_team_role_id in role_id or not owner_role_id in role_id:
        embed = Embed(
            title='**You do not have permission!**',
            description='You do not have permission to use this command.',
            color=0xff0000
        )
        await event.message.respond(embed=embed)
        return

    viewable = Permissions(Permissions.VIEW_CHANNEL | Permissions.SEND_MESSAGES)

    global ticket_counter
    ticket_counter += 1
    values_sql['ticket_counter'] = ticket_counter

    channel: GuildChannel = await client.rest.create_guild_text_channel(
        guild=event.guild_id,
        name=f'ticket-{ticket_counter}',
        category=1054638384091504650,
        topic=f'Ticket created by {event.member.username}#{event.member.discriminator} ({event.member.id})'
    )

    ticket = Ticket(
        id=ticket_counter,
        owner=event.member.id,
        channel=channel.id,
        creation_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    )

    await client.rest.edit_permission_overwrite(
        channel=channel,
        target_type=PermissionOverwriteType.ROLE,
        target=member_role_id,
        allow=Permissions.NONE,
        deny=viewable
    )

    await client.rest.edit_permission_overwrite(
        channel=channel,
        target_type=PermissionOverwriteType.ROLE,
        target=staff_team_role_id,
        allow=viewable,
        deny=Permissions.NONE
    )

    await client.rest.edit_permission_overwrite(
        channel=channel,
        target_type=PermissionOverwriteType.ROLE,
        target=owner_role_id,
        allow=viewable,
        deny=Permissions.NONE
    )

    await client.rest.edit_permission_overwrite(
        channel=channel,
        target_type=PermissionOverwriteType.MEMBER,
        target=event.member.id,
        allow=viewable,
        deny=Permissions.NONE
    )

    tickets_sql[channel.id] = encode(ticket)
    tickets[channel.id] = ticket

    embed = Embed(
        title='**Ticket Created**',
        description=f'Your ticket has been created. Please wait for a staff member to respond.',
        color=0x00ff00
    )
    await event.message.respond(embed=embed)


async def ticket_close(client: GatewayBot, event: GuildMessageCreateEvent):
    if event.is_bot or not event.content:
        return

    role_id = event.member.role_ids

    if not staff_team_role_id in role_id or not owner_role_id in role_id:
        embed = Embed(
            title='**You do not have permission!**',
            description='You do not have permission to use this command.',
            color=0xff0000
        )
        await event.message.respond(embed=embed)
        return

    if not event.channel_id in tickets:
        embed = Embed(
            title='**This is not a ticket!**',
            description='This is not a ticket channel.',
            color=0xff0000
        )
        await event.message.respond(embed=embed)
        return

    ticket = tickets[event.channel_id]

    if ticket.owner != event.member.id or owner_role_id not in role_id or staff_team_role_id not in role_id:
        embed = Embed(
            title='**You do not own this ticket!**',
            description='You do not own this ticket.',
            color=0xff0000
        )
        await event.message.respond(embed=embed)
        return

    # Send an embed saying the channel will delete in 15 seconds.
    embed = Embed(
        title='**Ticket Closing**',
        description='This ticket will be closed in 15 seconds.',
        color=0xff0000
    )
    await event.message.respond(embed=embed)

    # Wait 15 seconds.
    await asyncio.sleep(15)

    # Delete the channel.
    await client.rest.delete_channel(channel=event.channel_id)

    # Convert ticket object to archived ticket object.
    archived_ticket = ArchivedTicket(
        id=ticket.id,
        owner=ticket.owner,
        channel=ticket.channel,
        creation_time=ticket.creation_time,
        archive=ticket.archive
    )

    ticket_messages_long_string = ''
    for message in archived_ticket.archive.values():
        ticket_messages_long_string += f'[{message.timestamp}] {message.author} ({message.author_id}): {message.content}\n'

    # All that's needed for a successful response
    url = pbp.paste(pastebin_api_key, ticket_messages_long_string, "Ticket Archive")

    # Send message to archive channel containing the URL.
    embed = Embed(
        title='**Ticket Archive**',
        description=f'Ticket #{archived_ticket.id} has been archived.\n\n{url}',
        color=0x00ff00
    )
    await client.rest.create_message(
        channel=ticket_archive_channel_id,
        embed=embed
    )

    # Delete the ticket from the tickets dict.
    del tickets[event.channel_id]

    # Delete the ticket from the tickets_sql dict.
    del tickets_sql[event.channel_id]

    # Add the archived ticket to the archived_tickets dict.
    archived_tickets[event.channel_id] = archived_ticket

    # Add the archived ticket to the archived_tickets_sql dict.
    archived_tickets_sql[event.channel_id] = encode(archived_ticket)


async def ticket_archive(client: GatewayBot, event: GuildMessageCreateEvent):
    if event.is_bot or not event.content:
        return

    role_id = event.member.role_ids

    if not staff_team_role_id in role_id or not owner_role_id in role_id:
        embed = Embed(
            title='**You do not have permission!**',
            description='You do not have permission to use this command.',
            color=0xff0000
        )
        await event.message.respond(embed=embed)
        return

    # Command takes one argument, the ticket owner id.
    # The command then finds all the tickets belonging to the user, if any.
    # If there are no tickets belonging to the user, it will send an error message.

    if len(event.content.split(' ')) != 3:
        embed = Embed(
            title='**Invalid Arguments**',
            description='Invalid arguments. Please use the following format: `!ticket archive <user id>`',
            color=0xff0000
        )
        await event.message.respond(embed=embed)
        return

    user_id = event.content.split(' ')[2]

    if not user_id.isdigit():
        embed = Embed(
            title='**Invalid User ID!**',
            description='The user ID you provided is invalid.',
            color=0xff0000
        )
        await event.message.respond(embed=embed)
        return

    user_id = int(user_id)
    tickets_user = []

    for k, v in tickets_sql.items():
        ticket_temp = decode(v.encode('utf-8'))
        if ticket_temp.owner == user_id:
            tickets_user.append(ticket_temp)

    if not tickets_user:
        embed = Embed(
            title='**No Tickets Found!**',
            description='No tickets were found for this user.',
            color=0xff0000
        )
        await event.message.respond(embed=embed)
        return

    embed = Embed(
        title='**Tickets Found**',
        description=f'Found {len(tickets_user)} tickets for this user.',
        color=0x00ff00
    )

    for ticket in tickets_user:
        channel_ping = f'<#{ticket.channel}>'
        embed.add_field(
            name=f'Ticket {ticket.id}',
            value=f'Created at {ticket.creation_time}\nChannel: {channel_ping}\nChannel ID: {ticket.channel}',
            inline=False
        )

    await event.message.respond(embed=embed)


async def announce(client: GatewayBot, event: GuildMessageCreateEvent):
    if event.is_bot or not event.content:
        return

    role_id = event.member.role_ids

    if not staff_team_role_id in role_id or not owner_role_id in role_id:
        embed = Embed(
            title='**You do not have permission!**',
            description='You do not have permission to use this command.',
            color=0xff0000
        )
        await event.message.respond(embed=embed)
        return

    waiting_on_message.append(event.member.id)

    embed = Embed(
        title='**Announcement**',
        description='Please send the channel ID you''d like to post the message in.',
        color=0x00ff00
    )
    await event.message.respond(embed=embed)


from captcha.image import ImageCaptcha


async def captcha(client: GatewayBot, event: GuildMessageCreateEvent):
    if event.is_bot or not event.content:
        return

    role_id = event.member.role_ids

    if not staff_team_role_id in role_id or not owner_role_id in role_id:
        embed = Embed(
            title='**You do not have permission!**',
            description='You do not have permission to use this command.',
            color=0xff0000
        )
        await event.message.respond(embed=embed)
        return

    # This function is a test function.
    # Generate a random string with the above function.
    # Generate an image in /images/captcha.png with the captcha.
    random_string = generate_random_string(6)
    image = ImageCaptcha()
    data = image.generate(random_string)

    # Respond with the image.
    await event.message.respond(attachment=data)
