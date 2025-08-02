"""Administrative commands for co-owner management."""

import discord
from discord.ext import commands
from discord import app_commands
from typing import List
from ..utils.helpers import (
    create_success_embed, create_error_embed, create_embed
)


class AdminCommands(commands.Cog):
    """Administrative commands for managing co-owners."""
    
    def __init__(self, bot):
        self.bot = bot
        self.ticket_service = bot.ticket_service
    
    async def _check_owner_authorization(self, interaction: discord.Interaction) -> bool:
        """Check if user is the server owner or administrator."""
        if not interaction.guild:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "This command can only be used in a server."),
                ephemeral=True
            )
            return False
        
        # Check if user is server owner
        if interaction.guild.owner_id == interaction.user.id:
            return True
        
        # Check if user has administrator permissions
        if interaction.user.guild_permissions.administrator:
            return True
        
        await interaction.response.send_message(
            embed=create_error_embed(
                "Access Denied", 
                "Only the server owner or administrators can use this command."
            ),
            ephemeral=True
        )
        return False
    
    @app_commands.command(
        name="add-co-owner",
        description="Add a co-owner who can manage the ticket system (Owner only)"
    )
    @app_commands.describe(
        user="User to add as co-owner"
    )
    async def add_co_owner(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """Add a co-owner."""
        if not await self._check_owner_authorization(interaction):
            return
        
        # Debug information
        print(f"Debug: Guild owner ID: {interaction.guild.owner_id}")
        print(f"Debug: User ID: {interaction.user.id}")
        print(f"Debug: User is admin: {interaction.user.guild_permissions.administrator}")
        print(f"Debug: Target user ID: {user.id}")
        print(f"Debug: Target user is bot: {user.bot}")
        
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Invalid User",
                    "You cannot add yourself as a co-owner."
                ),
                ephemeral=True
            )
            return
        
        if user.bot:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Invalid User",
                    "You cannot add bots as co-owners."
                ),
                ephemeral=True
            )
            return
        
        try:
            # Check if already co-owner
            is_co_owner = await self.ticket_service.repository.is_co_owner(
                interaction.guild.id, 
                user.id
            )
            
            if is_co_owner:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Already Co-Owner",
                        f"{user.mention} is already a co-owner."
                    ),
                    ephemeral=True
                )
                return
            
            # Add co-owner
            await self.ticket_service.add_co_owner(
                interaction.guild.id,
                user.id,
                interaction.user.id
            )
            
            embed = create_success_embed(
                "Co-Owner Added",
                f"{user.mention} has been added as a co-owner.\n"
                "They can now manage the ticket system."
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Try to notify the new co-owner
            try:
                dm_embed = create_embed(
                    "Co-Owner Added",
                    f"You have been added as a co-owner of the ticket system in **{interaction.guild.name}**.\n"
                    "You can now use ticket management commands."
                )
                await user.send(embed=dm_embed)
            except (discord.Forbidden, discord.HTTPException):
                pass  # Ignore if can't send DM
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Operation Failed",
                    f"An error occurred: {str(e)}"
                ),
                ephemeral=True
            )
    
    @app_commands.command(
        name="remove-co-owner",
        description="Remove a co-owner (Owner only)"
    )
    @app_commands.describe(
        user="User to remove as co-owner"
    )
    async def remove_co_owner(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """Remove a co-owner."""
        if not await self._check_owner_authorization(interaction):
            return
        
        try:
            removed = await self.ticket_service.remove_co_owner(
                interaction.guild.id,
                user.id
            )
            
            if removed:
                embed = create_success_embed(
                    "Co-Owner Removed",
                    f"{user.mention} has been removed as a co-owner."
                )
                
                # Try to notify the removed co-owner
                try:
                    dm_embed = create_embed(
                        "Co-Owner Removed",
                        f"You have been removed as a co-owner of the ticket system in **{interaction.guild.name}**."
                    )
                    await user.send(embed=dm_embed)
                except (discord.Forbidden, discord.HTTPException):
                    pass  # Ignore if can't send DM
            else:
                embed = create_error_embed(
                    "Not Found",
                    f"{user.mention} is not a co-owner."
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Operation Failed",
                    f"An error occurred: {str(e)}"
                ),
                ephemeral=True
            )
    
    @app_commands.command(
        name="list-co-owners",
        description="List all co-owners (Owner only)"
    )
    async def list_co_owners(self, interaction: discord.Interaction):
        """List all co-owners."""
        if not await self._check_owner_authorization(interaction):
            return
        
        try:
            co_owners = await self.ticket_service.repository.get_co_owners(interaction.guild.id)
            
            if not co_owners:
                embed = create_embed(
                    "Co-Owners",
                    "No co-owners have been added to this server."
                )
            else:
                co_owner_list = []
                for co_owner in co_owners:
                    user = interaction.guild.get_member(co_owner.user_id)
                    if user:
                        assigned_by = interaction.guild.get_member(co_owner.assigned_by)
                        assigned_by_name = assigned_by.display_name if assigned_by else "Unknown"
                        co_owner_list.append(
                            f"• {user.mention} (added by {assigned_by_name})"
                        )
                    else:
                        co_owner_list.append(f"• User ID: {co_owner.user_id} (user left)")
                
                embed = create_embed(
                    "Co-Owners",
                    f"**Total:** {len(co_owners)}\n\n" + "\n".join(co_owner_list)
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Operation Failed",
                    f"An error occurred: {str(e)}"
                ),
                ephemeral=True
            )


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(AdminCommands(bot))
