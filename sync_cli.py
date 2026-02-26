#!/usr/bin/env python3
"""
🎭 Parody Critics - Synchronization CLI
Command-line interface for Jellyfin sync operations
"""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import our sync system
from utils import (
    setup_logging, get_logger, log_exception,
    SyncManager
)
from config import Config

# Initialize console
console = Console()

# Setup logging
setup_logging()
logger = get_logger('sync_cli')


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config-file', help='Path to config file', default='.env')
@click.pass_context
def cli(ctx, debug: bool, config_file: str):
    """🎭 Parody Critics - Jellyfin Sync CLI"""

    # Ensure context exists
    ctx.ensure_object(dict)

    # Reconfigure logging if debug is enabled
    if debug:
        setup_logging(log_level='DEBUG')
        logger.debug("Debug logging enabled")

    # Load configuration
    try:
        config = Config()
        ctx.obj['config'] = config
        logger.debug("Configuration loaded successfully")
    except Exception as e:
        console.print(f"[red]❌ Failed to load configuration: {str(e)}[/red]")
        console.print(f"[dim]Make sure {config_file} exists or run the setup wizard first.[/dim]")
        sys.exit(1)


@cli.command()
@click.option('--page-size', default=100, help='Number of items per page', type=int)
@click.option('--library-id', help='Specific library ID to sync')
@click.option('--dry-run', is_flag=True, help='Show what would be synced without making changes')
@click.pass_context
def sync(ctx, page_size: int, library_id: str, dry_run: bool):
    """🔄 Synchronize Jellyfin library with local database"""

    config = ctx.obj['config']

    # Show sync header
    console.print(Panel(
        "[bold blue]🎭 Jellyfin Library Synchronization[/bold blue]\n\n"
        f"Jellyfin URL: {config.JELLYFIN_URL}\n"
        f"Database: {config.PARODY_CRITICS_DB_PATH}\n"
        f"Page Size: {page_size} items\n"
        + (f"Library ID: {library_id}\n" if library_id else "Libraries: All Movies & Series\n")
        + ("[yellow]DRY RUN - No changes will be made[/yellow]" if dry_run else ""),
        style="bright_blue"
    ))

    if dry_run:
        console.print("[yellow]⚠️  Dry run mode - no actual sync will be performed[/yellow]")
        console.print("[dim]Use --no-dry-run to perform actual synchronization[/dim]")
        return

    # Confirm sync
    if not click.confirm("\n🚀 Start synchronization?"):
        console.print("[yellow]Sync cancelled by user[/yellow]")
        return

    # Run async sync
    asyncio.run(_run_sync(config, page_size, library_id))


async def _run_sync(config: Config, page_size: int, library_id: str):
    """Run the actual sync operation"""
    try:
        logger.info(f"Starting Jellyfin sync - URL: {config.JELLYFIN_URL}")

        async with SyncManager(
            jellyfin_url=config.JELLYFIN_URL,
            api_key=config.JELLYFIN_API_TOKEN,
            database_path=config.DATABASE_PATH
        ) as sync_manager:

            results = await sync_manager.sync_jellyfin_library(
                library_id=library_id,
                page_size=page_size
            )

            # Show final results
            _display_sync_results(results)

    except Exception as e:
        logger.error(f"Sync operation failed: {str(e)}")
        log_exception(logger, e, "Sync operation")
        console.print(f"\n[red]❌ Sync failed: {str(e)}[/red]")
        console.print("[dim]Check logs for detailed error information[/dim]")


def _display_sync_results(results: dict):
    """Display sync results in a formatted table"""
    console.print("\n")

    # Create results table
    results_table = Table(
        title="🎬 Sync Results Summary",
        show_header=True,
        header_style="bold green"
    )
    results_table.add_column("Metric", style="cyan")
    results_table.add_column("Count", style="bold")
    results_table.add_column("Description", style="dim")

    # Add result rows
    results_table.add_row(
        "📊 Total Processed",
        str(results['items_processed']),
        "Total items from Jellyfin"
    )
    results_table.add_row(
        "🆕 New Items",
        f"[green]{results['items_added']}[/green]",
        "Added to database"
    )
    results_table.add_row(
        "🔄 Updated Items",
        f"[yellow]{results['items_updated']}[/yellow]",
        "Existing items updated"
    )
    results_table.add_row(
        "⚡ Unchanged Items",
        f"[blue]{results.get('items_unchanged', 0)}[/blue]",
        "No changes needed"
    )

    if results['errors'] > 0:
        results_table.add_row(
            "❌ Errors",
            f"[red]{results['errors']}[/red]",
            "Items that failed processing"
        )

    # Additional info
    results_table.add_row(
        "🏥 Status",
        f"[green]{results['status']}[/green]" if results['status'] == 'completed' else f"[yellow]{results['status']}[/yellow]",
        f"Session: {results['session_id']}"
    )

    console.print(results_table)

    # Success message
    if results['errors'] == 0:
        console.print("\n[green]✅ Synchronization completed successfully![/green]")
    else:
        console.print(f"\n[yellow]⚠️  Sync completed with {results['errors']} errors - check logs for details[/yellow]")


@cli.command()
@click.option('--limit', default=10, help='Number of recent sync entries to show', type=int)
@click.pass_context
def history(ctx, limit: int):
    """📋 Show sync history"""

    config = ctx.obj['config']

    console.print(Panel(
        f"[bold blue]🕐 Sync History[/bold blue]\n\nShowing last {limit} sync operations",
        style="bright_blue"
    ))

    # Run async history fetch
    asyncio.run(_show_sync_history(config, limit))


async def _show_sync_history(config: Config, limit: int):
    """Show sync history from database"""
    try:
        async with SyncManager(
            jellyfin_url=config.JELLYFIN_URL,
            api_key=config.JELLYFIN_API_TOKEN,
            database_path=config.DATABASE_PATH
        ) as sync_manager:

            history_entries = await sync_manager.get_sync_history(limit=limit)

            if not history_entries:
                console.print("\n[dim]No sync history found[/dim]")
                return

            # Create history table
            history_table = Table(
                title="Sync History",
                show_header=True,
                header_style="bold magenta"
            )
            history_table.add_column("Date", style="cyan")
            history_table.add_column("Operation", style="white")
            history_table.add_column("Status", style="bold")
            history_table.add_column("Items", style="dim")
            history_table.add_column("Added/Updated", style="green")

            for entry in history_entries:
                # Format date
                started_at = entry['started_at']
                if isinstance(started_at, str):
                    date_str = started_at.split()[0]  # Just date part
                else:
                    date_str = str(started_at).split()[0]

                # Status with color
                status = entry['status']
                if status == 'completed':
                    status_display = f"[green]{status}[/green]"
                elif status == 'failed':
                    status_display = f"[red]{status}[/red]"
                else:
                    status_display = f"[yellow]{status}[/yellow]"

                # Items info
                items_processed = entry.get('items_processed', 0)
                items_added = entry.get('items_added', 0)
                items_updated = entry.get('items_updated', 0)

                history_table.add_row(
                    date_str,
                    entry['operation'],
                    status_display,
                    str(items_processed),
                    f"{items_added}/{items_updated}"
                )

            console.print(history_table)

    except Exception as e:
        logger.error(f"Failed to get sync history: {str(e)}")
        console.print(f"[red]❌ Failed to retrieve history: {str(e)}[/red]")


@cli.command()
@click.confirmation_option(prompt='⚠️  This will remove media items not found in Jellyfin. Continue?')
@click.pass_context
def cleanup(ctx):
    """🧹 Remove orphaned media items from database"""

    config = ctx.obj['config']

    console.print(Panel(
        "[bold yellow]🧹 Database Cleanup[/bold yellow]\n\n"
        "This will remove media items from the database that no longer exist in Jellyfin.",
        style="bright_yellow"
    ))

    # Run async cleanup
    asyncio.run(_run_cleanup(config))


async def _run_cleanup(config: Config):
    """Run cleanup operation"""
    try:
        async with SyncManager(
            jellyfin_url=config.JELLYFIN_URL,
            api_key=config.JELLYFIN_API_TOKEN,
            database_path=config.DATABASE_PATH
        ) as sync_manager:

            removed_count = await sync_manager.cleanup_orphaned_media()

            if removed_count > 0:
                console.print(f"\n[green]✅ Cleaned up {removed_count} orphaned media items[/green]")
            else:
                console.print("\n[blue]ℹ️  No orphaned media items found[/blue]")

    except Exception as e:
        logger.error(f"Cleanup operation failed: {str(e)}")
        console.print(f"[red]❌ Cleanup failed: {str(e)}[/red]")


@cli.command()
@click.pass_context
def status(ctx):
    """📊 Show sync status and database statistics"""

    config = ctx.obj['config']

    console.print(Panel(
        "[bold blue]📊 Sync Status[/bold blue]",
        style="bright_blue"
    ))

    # Run async status check
    asyncio.run(_show_status(config))


async def _show_status(config: Config):
    """Show status information"""
    try:
        async with SyncManager(
            jellyfin_url=config.JELLYFIN_URL,
            api_key=config.JELLYFIN_API_TOKEN,
            database_path=config.DATABASE_PATH
        ) as sync_manager:

            # Get database statistics
            cursor = sync_manager.db_connection.execute("""
                SELECT
                    COUNT(*) as total_media,
                    SUM(CASE WHEN type = 'movie' THEN 1 ELSE 0 END) as movies,
                    SUM(CASE WHEN type = 'series' THEN 1 ELSE 0 END) as series,
                    COUNT(jellyfin_id) as jellyfin_items
                FROM media
            """)
            stats = cursor.fetchone()

            # Get recent sync info
            recent_syncs = await sync_manager.get_sync_history(limit=1)

            # Create status table
            status_table = Table(
                title="Database Statistics",
                show_header=True,
                header_style="bold cyan"
            )
            status_table.add_column("Metric", style="white")
            status_table.add_column("Value", style="bold green")

            status_table.add_row("Total Media Items", str(stats['total_media']))
            status_table.add_row("Movies", str(stats['movies']))
            status_table.add_row("TV Series", str(stats['series']))
            status_table.add_row("Jellyfin-Linked Items", str(stats['jellyfin_items']))

            if recent_syncs:
                last_sync = recent_syncs[0]
                last_sync_date = str(last_sync['started_at']).split()[0]
                status_table.add_row("Last Sync", last_sync_date)
                status_table.add_row("Last Sync Status", last_sync['status'])

            console.print(status_table)

            # Jellyfin server info
            if sync_manager.jellyfin_client and sync_manager.jellyfin_client.server_info:
                server_info = sync_manager.jellyfin_client.server_info
                console.print("\n[bold blue]🎬 Jellyfin Server:[/bold blue]")
                console.print(f"  Name: {server_info.get('ServerName', 'Unknown')}")
                console.print(f"  Version: {server_info.get('Version', 'Unknown')}")
                console.print(f"  URL: {config.JELLYFIN_URL}")

    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        console.print(f"[red]❌ Failed to retrieve status: {str(e)}[/red]")


@cli.command()
def test():
    """🧪 Test sync system connectivity"""

    console.print(Panel(
        "[bold blue]🧪 Testing Sync System[/bold blue]",
        style="bright_blue"
    ))

    # Test imports
    try:
        from utils import SyncManager, JellyfinClient  # noqa: F401
        console.print("[green]✅ Sync system imports OK[/green]")
    except ImportError as e:
        console.print(f"[red]❌ Import error: {str(e)}[/red]")
        return

    # Test configuration
    try:
        config = Config()
        console.print("[green]✅ Configuration loaded OK[/green]")
        console.print(f"  Jellyfin URL: {config.JELLYFIN_URL}")
        console.print(f"  Database: {config.DATABASE_PATH}")
    except Exception as e:
        console.print(f"[red]❌ Configuration error: {str(e)}[/red]")
        return

    # Test database path
    db_path = Path(config.DATABASE_PATH)
    if db_path.parent.exists():
        console.print("[green]✅ Database directory exists[/green]")
    else:
        console.print(f"[yellow]⚠️  Database directory will be created: {db_path.parent}[/yellow]")

    console.print("\n[green]🎉 System tests passed! Ready to sync.[/green]")


if __name__ == "__main__":
    cli()