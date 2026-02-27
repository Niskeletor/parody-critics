#!/usr/bin/env python3
"""
🎭 Parody Critics - Synchronization Progress Display System
Visual progress tracking with Rich for Jellyfin sync operations
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timedelta
import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn,
    TaskProgressColumn, TimeRemainingColumn, TimeElapsedColumn,
    MofNCompleteColumn
)
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.align import Align

from .logger import get_logger

logger = get_logger('sync_progress')


@dataclass
class SyncStats:
    """Statistics for synchronization operations"""
    total_items: int = 0
    processed_items: int = 0
    new_items: int = 0
    updated_items: int = 0
    unchanged_items: int = 0
    errors: int = 0
    current_page: int = 0
    total_pages: int = 0
    start_time: Optional[datetime] = None
    items_per_second: float = 0.0
    estimated_completion: Optional[datetime] = None


class SyncProgressDisplay:
    """
    Rich-based progress display for Jellyfin synchronization

    Features:
    - Real-time progress bars with ETA
    - Statistics table with live updates
    - Color-coded status indicators
    - Performance metrics
    - Error tracking and display
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize progress display

        Args:
            console: Rich Console instance (creates new if None)
        """
        self.console = console or Console()
        self.stats = SyncStats()
        self.live: Optional[Live] = None
        self.layout: Optional[Layout] = None

        # Progress tracking
        self.progress: Optional[Progress] = None
        self.main_task_id: Optional[int] = None
        self.page_task_id: Optional[int] = None

        # Status tracking
        self.current_item: str = ""
        self.current_operation: str = ""
        self.errors: List[str] = []

        logger.debug("Initialized sync progress display")

    def _create_layout(self) -> Layout:
        """Create the Rich layout structure"""
        layout = Layout()

        # Split into header, main, and footer
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=8)
        )

        # Split main into progress and stats
        layout["main"].split_row(
            Layout(name="progress"),
            Layout(name="stats", minimum_size=40)
        )

        return layout

    def _create_progress_bar(self) -> Progress:
        """Create Rich progress bar with custom columns"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.fields[operation]}", justify="left"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            expand=True
        )

    def _create_header_panel(self) -> Panel:
        """Create header panel with title and status"""
        title = Text("🎭 Parody Critics - Jellyfin Sync", style="bold magenta")
        status = Text(f" {self.current_operation}", style="cyan")

        header_text = Text()
        header_text.append_text(title)
        if self.current_operation:
            header_text.append_text(status)

        return Panel(
            Align.center(header_text),
            style="bright_blue",
            padding=(0, 1)
        )

    def _create_stats_table(self) -> Table:
        """Create statistics table"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Statistic", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        # Calculate performance metrics
        if self.stats.start_time:
            elapsed = datetime.now() - self.stats.start_time
            elapsed_seconds = max(elapsed.total_seconds(), 1)
            self.stats.items_per_second = self.stats.processed_items / elapsed_seconds

            if self.stats.items_per_second > 0 and self.stats.total_items > self.stats.processed_items:
                remaining_items = self.stats.total_items - self.stats.processed_items
                remaining_seconds = remaining_items / self.stats.items_per_second
                self.stats.estimated_completion = datetime.now() + timedelta(seconds=remaining_seconds)

        # Add rows
        table.add_row("📊 Total Items", str(self.stats.total_items))
        table.add_row("✅ Processed", str(self.stats.processed_items))
        table.add_row("🆕 New Items", f"[green]{self.stats.new_items}[/green]")
        table.add_row("🔄 Updated Items", f"[yellow]{self.stats.updated_items}[/yellow]")
        table.add_row("⚡ Unchanged", f"[blue]{self.stats.unchanged_items}[/blue]")

        if self.stats.errors > 0:
            table.add_row("❌ Errors", f"[red]{self.stats.errors}[/red]")

        table.add_row("📄 Current Page", f"{self.stats.current_page}/{self.stats.total_pages}")
        table.add_row("⚡ Speed", f"{self.stats.items_per_second:.1f} items/sec")

        if self.stats.estimated_completion:
            eta_str = self.stats.estimated_completion.strftime("%H:%M:%S")
            table.add_row("⏰ ETA", eta_str)

        if self.current_item:
            # Truncate long item names
            item_display = self.current_item[:35] + "..." if len(self.current_item) > 35 else self.current_item
            table.add_row("🎬 Current", f"[italic]{item_display}[/italic]")

        return table

    def _create_error_panel(self) -> Optional[Panel]:
        """Create error panel if there are errors"""
        if not self.errors:
            return None

        # Show last 3 errors
        recent_errors = self.errors[-3:]
        error_text = "\n".join([f"❌ {error}" for error in recent_errors])

        if len(self.errors) > 3:
            error_text += f"\n... and {len(self.errors) - 3} more errors"

        return Panel(
            error_text,
            title="Recent Errors",
            style="red",
            padding=(0, 1)
        )

    def _update_display(self):
        """Update the live display with current data"""
        if not self.layout:
            return

        # Update header
        self.layout["header"].update(self._create_header_panel())

        # Update progress bar
        if self.progress:
            self.layout["progress"].update(self.progress)

        # Update stats table
        self.layout["stats"].update(self._create_stats_table())

        # Update footer with errors if any
        error_panel = self._create_error_panel()
        if error_panel:
            self.layout["footer"].update(error_panel)
        else:
            self.layout["footer"].update("")

    @contextmanager
    def sync_session(self, operation: str = "Jellyfin Synchronization"):
        """
        Context manager for sync session with live display

        Args:
            operation: Description of the sync operation
        """
        logger.info(f"Starting sync session: {operation}")
        self.current_operation = operation
        self.stats = SyncStats(start_time=datetime.now())

        # Create layout and progress
        self.layout = self._create_layout()
        self.progress = self._create_progress_bar()

        # Create main progress task
        self.main_task_id = self.progress.add_task(
            description="Overall Progress",
            total=100,  # Will be updated when we know total items
            operation=operation
        )

        # Create page progress task
        self.page_task_id = self.progress.add_task(
            description="Current Page",
            total=100,
            operation="Loading..."
        )

        try:
            with Live(
                self.layout,
                console=self.console,
                refresh_per_second=4,
                transient=True
            ) as live:
                self.live = live
                self._update_display()
                yield self

        finally:
            self.live = None
            logger.info(f"Completed sync session: {operation}")
            self._print_final_summary()

    def set_total_items(self, total: int, total_pages: int = 1):
        """Set the total number of items to process"""
        self.stats.total_items = total
        self.stats.total_pages = total_pages

        if self.progress and self.main_task_id is not None:
            self.progress.update(self.main_task_id, total=total)

        logger.debug(f"Set total items: {total} across {total_pages} pages")

    def update_page_progress(self, current_page: int, total_pages: int, page_items: int):
        """Update page-level progress"""
        self.stats.current_page = current_page
        self.stats.total_pages = total_pages

        if self.progress and self.page_task_id is not None:
            page_progress = (current_page / total_pages) * 100
            self.progress.update(
                self.page_task_id,
                completed=page_progress,
                operation=f"Page {current_page}/{total_pages} ({page_items} items)"
            )

        self._update_display()

    def update_item_progress(self, item_name: str, operation: str = "Processing"):
        """Update current item being processed"""
        self.current_item = item_name
        self.stats.processed_items += 1

        if self.progress and self.main_task_id is not None:
            self.progress.update(self.main_task_id, completed=self.stats.processed_items)

        logger.debug(f"{operation}: {item_name}")
        self._update_display()

    def record_new_item(self, item_name: str):
        """Record a new item added to database"""
        self.stats.new_items += 1
        self.update_item_progress(item_name, "Added")

    def record_updated_item(self, item_name: str):
        """Record an item updated in database"""
        self.stats.updated_items += 1
        self.update_item_progress(item_name, "Updated")

    def record_unchanged_item(self, item_name: str):
        """Record an item that didn't need updates"""
        self.stats.unchanged_items += 1
        self.update_item_progress(item_name, "Unchanged")

    def record_error(self, error_message: str, item_name: str = ""):
        """Record an error during processing"""
        self.stats.errors += 1
        error_text = f"{error_message}"
        if item_name:
            error_text += f" (Item: {item_name})"

        self.errors.append(error_text)
        logger.error(f"Sync error: {error_text}")
        self._update_display()

    def _print_final_summary(self):
        """Print final summary after sync completion"""
        if not self.stats.start_time:
            return

        elapsed = datetime.now() - self.stats.start_time

        # Create summary table
        summary_table = Table(show_header=True, header_style="bold green")
        summary_table.add_column("📊 Sync Summary", style="cyan")
        summary_table.add_column("Result", style="white")

        summary_table.add_row("⏱️ Duration", str(elapsed).split('.')[0])
        summary_table.add_row("📊 Total Items", str(self.stats.total_items))
        summary_table.add_row("✅ Processed", str(self.stats.processed_items))
        summary_table.add_row("🆕 New Items", f"[green]{self.stats.new_items}[/green]")
        summary_table.add_row("🔄 Updated Items", f"[yellow]{self.stats.updated_items}[/yellow]")
        summary_table.add_row("⚡ Unchanged", f"[blue]{self.stats.unchanged_items}[/blue]")
        summary_table.add_row("⚡ Average Speed", f"{self.stats.items_per_second:.1f} items/sec")

        if self.stats.errors > 0:
            summary_table.add_row("❌ Errors", f"[red]{self.stats.errors}[/red]")

        # Display summary
        self.console.print("\n")
        self.console.print(Panel(
            summary_table,
            title="🎭 Synchronization Complete",
            style="green",
            padding=(1, 2)
        ))

        # Show errors if any
        if self.errors:
            self.console.print(f"\n[red]⚠️  {len(self.errors)} errors occurred during sync:[/red]")
            for i, error in enumerate(self.errors[-5:], 1):  # Show last 5 errors
                self.console.print(f"[red]{i}.[/red] {error}")
            if len(self.errors) > 5:
                self.console.print(f"[dim]... and {len(self.errors) - 5} more errors[/dim]")


class ProgressCallback:
    """Callback adapter for Jellyfin client progress updates"""

    def __init__(self, progress_display: SyncProgressDisplay):
        self.progress_display = progress_display

    def __call__(self, current_page: int, total_pages: int, page_items: int):
        """Called by Jellyfin client for page progress updates"""
        self.progress_display.update_page_progress(current_page, total_pages, page_items)


# Convenience function for simple progress tracking
def create_sync_progress(console: Optional[Console] = None) -> SyncProgressDisplay:
    """
    Create a new sync progress display instance

    Args:
        console: Rich Console instance (optional)

    Returns:
        Configured SyncProgressDisplay instance
    """
    return SyncProgressDisplay(console)


# Example usage demonstration
async def demo_progress():
    """Demonstrate the progress system"""
    import random

    progress_display = create_sync_progress()

    with progress_display.sync_session("Demo Sync Operation"):
        # Simulate discovering total items
        total_items = 150
        total_pages = 6
        progress_display.set_total_items(total_items, total_pages)

        # Simulate processing pages
        processed = 0
        for page in range(1, total_pages + 1):
            page_items = min(25, total_items - processed)
            progress_display.update_page_progress(page, total_pages, page_items)

            # Simulate processing items in this page
            for i in range(page_items):
                processed += 1
                item_name = f"Movie {processed:03d}: The Amazing Adventure"

                # Simulate different outcomes
                rand = random.random()
                if rand < 0.4:
                    progress_display.record_new_item(item_name)
                elif rand < 0.7:
                    progress_display.record_updated_item(item_name)
                else:
                    progress_display.record_unchanged_item(item_name)

                # Simulate occasional errors
                if random.random() < 0.05:
                    progress_display.record_error("Failed to process metadata", item_name)

                # Simulate processing time
                await asyncio.sleep(0.1)


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_progress())