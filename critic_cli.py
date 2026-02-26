#!/usr/bin/env python3
"""
🎭 Parody Critics - Critic Generation CLI
Command-line interface for generating movie and TV series reviews with AI critics
"""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
import sqlite3

# Import our systems
from utils import setup_logging, get_logger, log_exception
from api.llm_manager import CriticGenerationManager
from config import Config

# Initialize console and logging
console = Console()
setup_logging()
logger = get_logger('critic_cli')


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config-file', help='Path to config file', default='.env')
@click.pass_context
def cli(ctx, debug: bool, config_file: str):
    """🎭 Parody Critics - AI Movie & TV Critics CLI"""

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
@click.argument('title', required=False)
@click.option('--character', '-c', default='Marco Aurelio',
              type=click.Choice(['Marco Aurelio', 'Rosario Costras'], case_sensitive=False),
              help='Character to generate the review')
@click.option('--year', '-y', type=int, help='Year of the movie/series')
@click.option('--type', '-t', 'media_type', default='movie',
              type=click.Choice(['movie', 'series'], case_sensitive=False),
              help='Type of media')
@click.option('--genres', '-g', help='Genres (comma-separated)')
@click.option('--overview', '-o', help='Plot overview/synopsis')
@click.option('--from-db', is_flag=True, help='Select from database')
@click.option('--save', is_flag=True, help='Save generated review to database')
@click.pass_context
def generate(ctx, title: str, character: str, year: int, media_type: str,
            genres: str, overview: str, from_db: bool, save: bool):
    """🎬 Generate a critic review for a movie or TV series"""

    config = ctx.obj['config']

    # Header
    console.print(Panel(
        f"[bold blue]🎭 Parody Critics - Review Generation[/bold blue]\n\n"
        f"Character: [bold]{character}[/bold]\n"
        f"LLM Models: {config.LLM_PRIMARY_MODEL} → {config.LLM_SECONDARY_MODEL}",
        style="bright_blue"
    ))

    # Get media information
    if from_db and not title:
        media_info = _select_from_database(config)
        if not media_info:
            console.print("[yellow]No media selected from database[/yellow]")
            return
    elif from_db and title:
        media_info = _search_in_database(title, config)
        if not media_info:
            console.print(f"[red]❌ '{title}' not found in database[/red]")
            return
    else:
        if not title:
            title = click.prompt("🎬 Movie/Series title", type=str)

        media_info = {
            'title': title,
            'year': year or click.prompt("📅 Year", type=int, default=2023),
            'type': media_type,
            'genres': genres or click.prompt("🎭 Genres", default="Drama", show_default=True),
            'overview': overview or click.prompt("📝 Plot overview", default="", show_default=False) or None
        }

    # Generate the review
    asyncio.run(_generate_review(config, character, media_info, save))


@cli.command()
@click.option('--limit', '-l', default=10, help='Number of recent reviews to show')
@click.pass_context
def history(ctx, limit: int):
    """📋 Show recent generated reviews"""

    config = ctx.obj['config']

    console.print(Panel(
        f"[bold blue]📋 Recent Reviews History[/bold blue]\n\nShowing last {limit} generated reviews",
        style="bright_blue"
    ))

    try:
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT c.*, m.title, m.year, m.type, ch.name as character_name
                FROM critics c
                JOIN media m ON c.media_id = m.id
                JOIN characters ch ON c.character_id = ch.id
                ORDER BY c.generated_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            reviews = cursor.fetchall()

        if not reviews:
            console.print("\n[dim]No reviews found in database[/dim]")
            return

        # Create history table
        history_table = Table(
            title="Recent Reviews",
            show_header=True,
            header_style="bold magenta"
        )
        history_table.add_column("Date", style="cyan")
        history_table.add_column("Media", style="white")
        history_table.add_column("Character", style="yellow")
        history_table.add_column("Rating", style="green")
        history_table.add_column("Preview", style="dim")

        for review in reviews:
            date_str = review['generated_at'].split()[0] if review['generated_at'] else 'Unknown'
            media_title = f"{review['title']} ({review['year']})"
            preview = review['content'][:50] + "..." if len(review['content']) > 50 else review['content']

            history_table.add_row(
                date_str,
                media_title,
                review['character_name'],
                f"{review['rating']}/10",
                preview
            )

        console.print(history_table)

    except Exception as e:
        logger.error(f"Failed to get review history: {str(e)}")
        console.print(f"[red]❌ Failed to retrieve history: {str(e)}[/red]")


@cli.command()
@click.pass_context
def status(ctx):
    """📊 Show LLM system status"""

    config = ctx.obj['config']

    console.print(Panel(
        "[bold blue]📊 LLM System Status[/bold blue]",
        style="bright_blue"
    ))

    asyncio.run(_show_llm_status(config))


@cli.command()
@click.argument('search_term')
@click.pass_context
def search(ctx, search_term: str):
    """🔍 Search media in database"""

    config = ctx.obj['config']

    console.print(Panel(
        f"[bold blue]🔍 Searching Media[/bold blue]\n\nSearching for: '{search_term}'",
        style="bright_blue"
    ))

    try:
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, title, year, type, genres
                FROM media
                WHERE title LIKE ? OR genres LIKE ?
                ORDER BY title
                LIMIT 20
                """,
                (f'%{search_term}%', f'%{search_term}%')
            )
            results = cursor.fetchall()

        if not results:
            console.print(f"\n[yellow]No media found matching '{search_term}'[/yellow]")
            return

        # Create results table
        results_table = Table(
            title="Search Results",
            show_header=True,
            header_style="bold green"
        )
        results_table.add_column("ID", style="cyan")
        results_table.add_column("Title", style="white")
        results_table.add_column("Year", style="yellow")
        results_table.add_column("Type", style="blue")
        results_table.add_column("Genres", style="dim")

        for item in results:
            results_table.add_row(
                str(item['id']),
                item['title'],
                str(item['year']) if item['year'] else 'Unknown',
                item['type'].title() if item['type'] else 'Unknown',
                item['genres'] if item['genres'] else 'Unknown'
            )

        console.print(results_table)

    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        console.print(f"[red]❌ Search failed: {str(e)}[/red]")


@cli.command()
@click.pass_context
def test(ctx):
    """🧪 Test LLM connectivity and character generation"""

    config = ctx.obj['config']

    console.print(Panel(
        "[bold blue]🧪 Testing LLM System[/bold blue]",
        style="bright_blue"
    ))

    asyncio.run(_test_system(config))


# Helper functions

def _select_from_database(config: Config) -> dict:
    """Interactive selection from database"""
    try:
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, title, year, type FROM media ORDER BY title LIMIT 20"
            )
            media_list = cursor.fetchall()

        if not media_list:
            console.print("[red]❌ No media found in database[/red]")
            return None

        console.print("\n[bold]📚 Available Media:[/bold]")
        for i, item in enumerate(media_list, 1):
            console.print(f"  {i:2d}. {item['title']} ({item['year']}) - {item['type'].title()}")

        choice = click.prompt(
            "\nSelect media (number)",
            type=click.IntRange(1, len(media_list))
        )

        selected = media_list[choice - 1]
        return dict(selected)

    except Exception as e:
        logger.error(f"Database selection failed: {str(e)}")
        console.print(f"[red]❌ Database error: {str(e)}[/red]")
        return None


def _search_in_database(title: str, config: Config) -> dict:
    """Search for specific title in database"""
    try:
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM media WHERE title LIKE ? LIMIT 1",
                (f'%{title}%',)
            )
            result = cursor.fetchone()

        return dict(result) if result else None

    except Exception as e:
        logger.error(f"Database search failed: {str(e)}")
        return None


async def _generate_review(config: Config, character: str, media_info: dict, save: bool):
    """Generate review using LLM"""

    logger.info(f"Starting review generation - Character: {character}, Media: {media_info['title']}")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=True
        ) as progress:

            task = progress.add_task(
                f"🎭 {character} is reviewing '{media_info['title']}'...",
                total=None
            )

            # Initialize LLM manager
            llm_manager = CriticGenerationManager()

            # Generate the review
            result = await llm_manager.generate_critic(character, media_info)

            progress.update(task, completed=True)

        if result['success']:
            # Parse the review
            parsed_review = llm_manager.parse_critic_response(
                result['response'],
                character,
                media_info
            )

            # Display the review
            _display_review(result, parsed_review, media_info)

            # Save if requested
            if save:
                _save_review_to_database(config, parsed_review, media_info, character)

        else:
            console.print(f"\n[red]❌ Review generation failed[/red]")
            console.print(f"Error: {result.get('error', 'Unknown error')}")

            # Show attempts
            if 'attempts' in result:
                console.print(f"\n[dim]Attempts made:[/dim]")
                for attempt in result['attempts']:
                    status_color = "green" if attempt['status'] == 'success' else "red"
                    console.print(f"  • {attempt['endpoint']} ({attempt['model']}): [{status_color}]{attempt['status']}[/{status_color}]")

    except Exception as e:
        logger.error(f"Review generation failed: {str(e)}")
        log_exception(logger, e, "Review generation")
        console.print(f"[red]❌ Generation failed: {str(e)}[/red]")


def _display_review(result: dict, parsed_review: dict, media_info: dict):
    """Display generated review"""

    console.print(f"\n🎉 [bold green]Review Generated![/bold green]")

    # Review info panel
    info_panel = Panel(
        f"[bold]{media_info['title']}[/bold] ({media_info.get('year', 'Unknown')})\n"
        f"Type: {media_info.get('type', 'Unknown').title()}\n"
        f"Character: [bold]{result['character']}[/bold]\n"
        f"Model: {result['model_used']}\n"
        f"Generation Time: {result['generation_time']:.1f}s\n"
        f"Rating: [bold yellow]{parsed_review['rating']}/10[/bold yellow]",
        title="📊 Review Info",
        style="blue"
    )

    console.print(info_panel)

    # Review content
    review_panel = Panel(
        parsed_review['content'],
        title=f"🎭 {result['character']}'s Review",
        style="green"
    )

    console.print(review_panel)


def _save_review_to_database(config: Config, parsed_review: dict, media_info: dict, character: str):
    """Save review to database"""
    try:
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            # Get or create character
            cursor = conn.execute(
                "SELECT id FROM characters WHERE name = ?",
                (character,)
            )
            char_row = cursor.fetchone()

            if not char_row:
                cursor = conn.execute(
                    "INSERT INTO characters (name, description) VALUES (?, ?)",
                    (character, f"AI critic character: {character}")
                )
                character_id = cursor.lastrowid
            else:
                character_id = char_row[0]

            # Get media ID
            media_id = media_info.get('id')
            if not media_id:
                console.print("[yellow]⚠️  Media not in database - review not saved[/yellow]")
                return

            # Save review
            conn.execute(
                """
                INSERT INTO critics (media_id, character_id, rating, content, generated_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (media_id, character_id, parsed_review['rating'], parsed_review['content'])
            )

            conn.commit()
            console.print("[green]✅ Review saved to database[/green]")

    except Exception as e:
        logger.error(f"Failed to save review: {str(e)}")
        console.print(f"[red]❌ Failed to save review: {str(e)}[/red]")


async def _show_llm_status(config: Config):
    """Show LLM system status"""
    try:
        llm_manager = CriticGenerationManager()
        status = await llm_manager.get_system_status()

        # Create status table
        status_table = Table(
            title="LLM System Status",
            show_header=True,
            header_style="bold cyan"
        )
        status_table.add_column("Component", style="white")
        status_table.add_column("Status", style="bold")
        status_table.add_column("Details", style="dim")

        # Add endpoint statuses
        for endpoint_name, endpoint_data in status['endpoints'].items():
            status_color = "green" if endpoint_data['status'] == 'healthy' else "red"
            status_table.add_row(
                endpoint_name,
                f"[{status_color}]{endpoint_data['status']}[/{status_color}]",
                f"Model: {endpoint_data['model']}, Priority: {endpoint_data['priority']}"
            )

        # Add system summary
        system_color = "green" if status['system_status'] == 'operational' else "red"
        status_table.add_row(
            "Overall System",
            f"[{system_color}]{status['system_status']}[/{system_color}]",
            f"{status['healthy_endpoints']}/{status['total_endpoints']} endpoints healthy"
        )

        console.print(status_table)

        # Show statistics if available
        stats = status.get('statistics', {})
        if stats.get('total_requests', 0) > 0:
            console.print(f"\n[bold]📊 Usage Statistics:[/bold]")
            console.print(f"  Total Requests: {stats['total_requests']}")
            console.print(f"  Success Rate: {stats['successful_requests']}/{stats['total_requests']}")
            console.print(f"  Average Time: {stats.get('total_time', 0) / max(stats['successful_requests'], 1):.2f}s")

    except Exception as e:
        logger.error(f"Failed to get system status: {str(e)}")
        console.print(f"[red]❌ Status check failed: {str(e)}[/red]")


async def _test_system(config: Config):
    """Test the LLM system"""
    try:
        llm_manager = CriticGenerationManager()

        # Health check
        console.print("🏥 Checking LLM health...")
        status = await llm_manager.get_system_status()

        healthy_endpoints = status['healthy_endpoints']
        total_endpoints = status['total_endpoints']

        if healthy_endpoints > 0:
            console.print(f"[green]✅ {healthy_endpoints}/{total_endpoints} endpoints healthy[/green]")

            # Test generation
            console.print("\n🧪 Testing review generation...")

            test_media = {
                'title': 'The Matrix',
                'year': 1999,
                'type': 'movie',
                'genres': 'Action, Sci-Fi',
                'overview': 'A computer hacker learns from mysterious rebels about the true nature of reality.'
            }

            result = await llm_manager.generate_critic('Marco Aurelio', test_media)

            if result['success']:
                console.print(f"[green]✅ Test generation successful![/green]")
                console.print(f"Model used: {result['model_used']}")
                console.print(f"Generation time: {result['generation_time']:.1f}s")

                # Show preview
                preview = result['response'][:100] + "..." if len(result['response']) > 100 else result['response']
                console.print(f"\n[dim]Preview: {preview}[/dim]")
            else:
                console.print(f"[red]❌ Test generation failed[/red]")
                console.print(f"Error: {result.get('error', 'Unknown error')}")
        else:
            console.print(f"[red]❌ No healthy endpoints available[/red]")

    except Exception as e:
        logger.error(f"System test failed: {str(e)}")
        console.print(f"[red]❌ System test failed: {str(e)}[/red]")


if __name__ == "__main__":
    cli()