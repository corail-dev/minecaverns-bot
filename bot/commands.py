import asyncio

from hikari import GatewayBot, GuildChannel, GuildMessageCreateEvent, Embed, EmbedField, PermissionOverwriteType, Permissions, PermissionOverwrite, Snowflake
from sqlitedict import SqliteDict
from jsonpickle import encode, decode
from dataclasses import dataclass
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

# Fetch all string values in tickets_sql and decode them into Ticket objects.
for key, value in tickets_sql.items():
    tickets[key] = decode(value.encode('utf-8'))


# Fetch all string values in archived_tickets_sql and decode them into Ticket objects.
for key, value in archived_tickets_sql.items():
    archived_tickets[key] = decode(value.encode('utf-8'))


@dataclass(frozen=True)
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

    ticket = Ticket(
        id=ticket_counter,
        owner=event.member.id,
        channel=0,
        creation_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    )

    channel: GuildChannel = await client.rest.create_guild_text_channel(
        guild=event.guild_id,
        name=f'ticket-{ticket_counter}',
        category=1054638384091504650,
        topic=f'Ticket created by {event.member.username}#{event.member.discriminator} ({event.member.id})'
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

    # Delete the ticket from the tickets dict.
    del tickets[event.channel_id]

    # Delete the ticket from the tickets_sql dict.
    del tickets_sql[event.channel_id]

    # Add the archived ticket to the archived_tickets dict.
    archived_tickets[event.channel_id] = archived_ticket

    # Add the archived ticket to the archived_tickets_sql dict.
    archived_tickets_sql[event.channel_id] = encode(archived_ticket)