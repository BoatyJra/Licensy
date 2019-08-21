import math
import logging
import traceback
import discord
from discord.ext import commands
from discord.errors import Forbidden
from helpers.errors import RoleNotFound, DefaultGuildRoleNotSet, DatabaseMissingData
from helpers import embed_handler

logger = logging.getLogger(__name__)


class CmdErrors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # If command has local error handler, return
        if hasattr(ctx.command, "on_error"):
            return

        # Get the original exception
        error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Command not found.")
            return

        if isinstance(error, commands.BotMissingPermissions):
            """
            Note that this is only for checks of the command , specifically for bot_has_permissions 
            example @commands.bot_has_permissions(administrator=True)
            It will not work for example if in command role.edit is called but bot doesn't have manage role permission.
            In that case a simple "Forbidden" will be raised.
            
            """
            missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_perms]
            if len(missing) > 2:
                fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            _message = f"I need the **{fmt}** permission(s) to run this command."
            await ctx.send(_message)
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send("This command has been disabled.")
            return

        if isinstance(error, commands.CommandOnCooldown):
            # Cooldowns are ignored for developers
            if ctx.message.author.id in self.bot.config.get_developers().values():
                # reinvoke() bypasses error handlers so we surround it with try/catch and just
                # send errors to ctx
                try:
                    await ctx.reinvoke()
                except Exception as e:
                    await ctx.send(e)
                return
            else:
                await ctx.send(f"This command is on cooldown, please retry in {math.ceil(error.retry_after)}s.")
                return

        if isinstance(error, commands.MissingPermissions):
            """
            Note that this is only for checks of the command , example @commands.has_permissions(administrator=True)
            MissingPermissions is raised if check for permissions of the member who invoked the command has failed.
            
            """
            missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_perms]
            if len(missing) > 2:
                fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            _message = f"You need the **{fmt}** permission(s) to use this command."
            await ctx.send(_message)
            return

        if isinstance(error, commands.UserInputError):
            await ctx.send(f"Invalid command input: {error}")
            return

        if isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send("This command cannot be used in direct messages.")
            except discord.Forbidden:
                pass
            return

        if isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have permission to use this command.")
            return

        if isinstance(error, Forbidden):
            # 403 FORBIDDEN (error code: 50013): Missing Permissions
            if error.code == 50013:
                await ctx.send(f"{error}.\n"
                               f"Check role hierarchy - I can only manage roles below me.")
            # 403 FORBIDDEN (error code: 50007): Cannot send messages to this user.
            elif error.code == 50007:
                await ctx.send(f"{error}.\n"
                               f"Hint: Disabled DMs?")
            else:
                await ctx.send(f"{error}.")
            return

        if isinstance(error, RoleNotFound):
            await ctx.send(error.message)
            return

        if isinstance(error, DefaultGuildRoleNotSet):
            await ctx.send(f"Trying to use default guild license but: {error.message}")
            return

        if isinstance(error, DatabaseMissingData):
            await ctx.send(f"Critical database error: {error.message}")
            await self.log_traceback(ctx, error)
            return

        await self.log_traceback(ctx, error)
        await ctx.send(f"Ignoring exception **{error.__class__.__name__}** that happened while processing command "
                       f"**{ctx.command}**:\n{error}")

    async def log_traceback(self, ctx, error):
        error_type = type(error)
        exception_message = f"Ignoring {error_type} exception in command '{ctx.command}':{error}"
        traceback_message = traceback.format_exception(etype=error_type, value=error, tb=error.__traceback__)
        logger.critical(f"{exception_message}")
        logger.critical(traceback_message)
        if self.bot.is_ready():
            log_channel = self.bot.get_channel(self.bot.config.get_developer_log_channel_id())
            embed = embed_handler.log_embed(exception_message, ctx=ctx, title="Command error!")
            traceback_embed = embed_handler.traceback_embed(traceback_message)
            if log_channel is not None:
                await log_channel.send(embed=embed)
                await log_channel.send(embed=traceback_embed)


def setup(bot):
    bot.add_cog(CmdErrors(bot))
