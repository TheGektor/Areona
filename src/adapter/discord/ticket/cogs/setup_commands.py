"""Setup commands for ticket system configuration."""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
from ..domain.entities import TicketType
from ..utils.helpers import (
    create_success_embed, create_error_embed, create_embed,
    validate_channel_permissions
)


class SetupCommands(commands.Cog):
    """Commands for setting up the ticket system."""
    
    def __init__(self, bot):
        self.bot = bot
        self.ticket_service = bot.ticket_service
    
    async def _check_authorization(self, interaction: discord.Interaction) -> bool:
        """Check if user is authorized to use setup commands."""
        if not interaction.guild:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "This command can only be used in a server."),
                ephemeral=True
            )
            return False
        
        is_authorized = await self.ticket_service.is_authorized(
            interaction.guild, 
            interaction.user
        )
        
        if not is_authorized:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Access Denied", 
                    "Only the server owner or co-owners can use this command."
                ),
                ephemeral=True
            )
            return False
        
        return True
    
    @app_commands.command(
        name="ticket-setup",
        description="Configure the ticket system for this server"
    )
    @app_commands.describe(
        ticket_type="Type of ticket system (simple or form)",
        welcome_message="Welcome message for new tickets",
        target_channel="Channel for form submissions (required for form type)"
    )
    async def ticket_setup(
        self,
        interaction: discord.Interaction,
        ticket_type: str,
        welcome_message: str,
        target_channel: Optional[discord.TextChannel] = None
    ):
        """Setup ticket system configuration."""
        if not await self._check_authorization(interaction):
            return
        
        # Validate ticket type
        try:
            ticket_type_enum = TicketType(ticket_type.lower())
        except ValueError:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Invalid Ticket Type",
                    "Ticket type must be either 'simple' or 'form'."
                ),
                ephemeral=True
            )
            return
        
        # Validate target channel for form type
        if ticket_type_enum == TicketType.FORM and not target_channel:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Target Channel Required",
                    "A target channel is required for form-type tickets."
                ),
                ephemeral=True
            )
            return
        
        # Check bot permissions in target channel
        if target_channel and not validate_channel_permissions(target_channel, interaction.guild.me):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Insufficient Permissions",
                    f"I don't have the necessary permissions in {target_channel.mention}. "
                    "Please ensure I can read messages, send messages, embed links, and manage channels."
                ),
                ephemeral=True
            )
            return
        
        try:
            # Save settings
            settings = await self.ticket_service.setup_guild_settings(
                guild_id=interaction.guild.id,
                ticket_type=ticket_type_enum,
                welcome_message=welcome_message,
                target_channel_id=target_channel.id if target_channel else None
            )
            
            # Create success embed
            fields = [
                ("Ticket Type", ticket_type_enum.value.title(), True),
                ("Welcome Message", welcome_message[:100] + "..." if len(welcome_message) > 100 else welcome_message, False)
            ]
            
            if target_channel:
                fields.append(("Target Channel", target_channel.mention, True))
            
            embed = create_success_embed(
                "Ticket System Configured",
                "The ticket system has been successfully configured for this server."
            )
            
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Configuration Failed",
                    f"An error occurred while configuring the ticket system: {str(e)}"
                ),
                ephemeral=True
            )
    
    @app_commands.command(
        name="ticket-questions",
        description="Set up form questions for form-type tickets"
    )
    @app_commands.describe(
        questions="Questions separated by semicolons (;). Max 10 questions."
    )
    async def ticket_questions(
        self,
        interaction: discord.Interaction,
        questions: str
    ):
        """Setup form questions."""
        if not await self._check_authorization(interaction):
            return
        
        # Parse questions
        question_list = [q.strip() for q in questions.split(';') if q.strip()]
        
        if not question_list:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "No Questions Provided",
                    "Please provide at least one question."
                ),
                ephemeral=True
            )
            return
        
        try:
            # Save questions
            form_questions = await self.ticket_service.setup_form_questions(
                interaction.guild.id, 
                question_list
            )
            
            # Create response embed
            questions_text = "\n".join([
                f"{i}. {q.text}" 
                for i, q in enumerate(form_questions, 1)
            ])
            
            embed = create_success_embed(
                "Form Questions Configured",
                f"Successfully configured {len(form_questions)} questions."
            )
            embed.add_field(
                name="Questions",
                value=questions_text[:1024],  # Discord field limit
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError as e:
            await interaction.response.send_message(
                embed=create_error_embed("Invalid Input", str(e)),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Configuration Failed",
                    f"An error occurred: {str(e)}"
                ),
                ephemeral=True
            )
    
    @app_commands.command(
        name="ticket-roles",
        description="Manage roles that can access tickets"
    )
    @app_commands.describe(
        action="Action to perform (add or remove)",
        role="Role to add or remove"
    )
    async def ticket_roles(
        self,
        interaction: discord.Interaction,
        action: str,
        role: discord.Role
    ):
        """Manage ticket roles."""
        if not await self._check_authorization(interaction):
            return
        
        action = action.lower()
        if action not in ['add', 'remove']:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Invalid Action",
                    "Action must be either 'add' or 'remove'."
                ),
                ephemeral=True
            )
            return
        
        try:
            if action == 'add':
                await self.ticket_service.add_ticket_role(interaction.guild.id, role.id)
                embed = create_success_embed(
                    "Role Added",
                    f"Role {role.mention} has been added to ticket access."
                )
            else:  # remove
                removed = await self.ticket_service.remove_ticket_role(interaction.guild.id, role.id)
                if removed:
                    embed = create_success_embed(
                        "Role Removed",
                        f"Role {role.mention} has been removed from ticket access."
                    )
                else:
                    embed = create_error_embed(
                        "Role Not Found",
                        f"Role {role.mention} was not in the ticket access list."
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
        name="ticket-status",
        description="View current ticket system configuration"
    )
    async def ticket_status(self, interaction: discord.Interaction):
        """View ticket system status."""
        if not await self._check_authorization(interaction):
            return
        
        try:
            # Get settings
            settings = await self.ticket_service.get_guild_settings(interaction.guild.id)
            
            if not settings:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Not Configured",
                        "The ticket system has not been configured for this server. "
                        "Use `/ticket-setup` to get started."
                    ),
                    ephemeral=True
                )
                return
            
            # Get additional info
            ticket_roles = await self.ticket_service.get_ticket_roles(interaction.guild.id)
            form_questions = await self.ticket_service.get_form_questions(interaction.guild.id)
            
            # Create status embed
            embed = create_embed(
                "Ticket System Status",
                "Current configuration for this server"
            )
            
            embed.add_field(
                name="Ticket Type",
                value=settings.ticket_type.value.title(),
                inline=True
            )
            
            embed.add_field(
                name="Welcome Message",
                value=settings.welcome_message[:100] + "..." if len(settings.welcome_message) > 100 else settings.welcome_message,
                inline=False
            )
            
            if settings.target_channel_id:
                channel = interaction.guild.get_channel(settings.target_channel_id)
                embed.add_field(
                    name="Target Channel",
                    value=channel.mention if channel else "Channel not found",
                    inline=True
                )
            
            # Ticket roles
            if ticket_roles:
                role_mentions = []
                for ticket_role in ticket_roles:
                    role = interaction.guild.get_role(ticket_role.role_id)
                    if role:
                        role_mentions.append(role.mention)
                
                embed.add_field(
                    name="Ticket Access Roles",
                    value=", ".join(role_mentions) if role_mentions else "None",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Ticket Access Roles",
                    value="None configured",
                    inline=False
                )
            
            # Form questions
            if settings.ticket_type == TicketType.FORM:
                embed.add_field(
                    name="Form Questions",
                    value=f"{len(form_questions)} questions configured",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Status Check Failed",
                    f"An error occurred: {str(e)}"
                ),
                ephemeral=True
            )

    @ticket_setup.autocomplete('ticket_type')
    async def ticket_type_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for ticket types."""
        choices = ['simple', 'form']
        return [
            app_commands.Choice(name=choice.title(), value=choice)
            for choice in choices
            if current.lower() in choice.lower()
        ]
    
    @ticket_roles.autocomplete('action')
    async def action_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for actions."""
        choices = ['add', 'remove']
        return [
            app_commands.Choice(name=choice.title(), value=choice)
            for choice in choices
            if current.lower() in choice.lower()
        ]


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(SetupCommands(bot))
