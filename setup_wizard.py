#!/usr/bin/env python3
"""
🧙‍♂️ Parody Critics Setup Wizard
Interactive CLI setup for first-time installation and configuration
"""

import os
import sys
import socket
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import click
import httpx
import questionary
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rprint

# Initialize Rich Console
console = Console()

class SetupWizard:
    def __init__(self):
        self.config = {}
        self.project_root = Path(__file__).parent
        self.env_file = self.project_root / '.env'
        self.env_example_file = self.project_root / '.env.example'

    def print_header(self):
        """Display fancy wizard header"""
        header_text = """
🎭 Parody Critics Setup Wizard 🧙‍♂️
=====================================

Welcome to the interactive setup for Parody Critics!
This wizard will help you configure your system step by step.

Let's create some hilarious movie reviews together! 🎬✨
        """
        console.print(Panel(header_text, style="bold blue", expand=False))

    def check_dependencies(self) -> Dict[str, bool]:
        """Check system dependencies and requirements"""
        console.print("\n[bold yellow]🔍 Step 1: Checking System Dependencies[/bold yellow]")

        checks = {
            "python": False,
            "sqlite": False,
            "port_8000": False,
            "virtual_env": False,
            "required_packages": False
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:

            # Python version check
            task = progress.add_task("Checking Python version...", total=None)
            try:
                python_version = sys.version_info
                if python_version >= (3, 11):
                    checks["python"] = True
                    progress.update(task, description=f"✅ Python {python_version.major}.{python_version.minor} detected")
                else:
                    progress.update(task, description=f"❌ Python {python_version.major}.{python_version.minor} - Need 3.11+")
            except Exception:
                progress.update(task, description="❌ Python version check failed")

            progress.remove_task(task)

            # SQLite check
            task = progress.add_task("Checking SQLite...", total=None)
            try:
                import sqlite3
                checks["sqlite"] = True
                progress.update(task, description="✅ SQLite available")
            except ImportError:
                progress.update(task, description="❌ SQLite not available")

            progress.remove_task(task)

            # Port availability check
            task = progress.add_task("Checking port 8000 availability...", total=None)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    result = s.connect_ex(('localhost', 8000))
                    if result != 0:  # Port is free
                        checks["port_8000"] = True
                        progress.update(task, description="✅ Port 8000 available")
                    else:
                        progress.update(task, description="⚠️ Port 8000 in use (can be configured)")
                        checks["port_8000"] = True  # Still OK, just needs config
            except Exception:
                progress.update(task, description="✅ Port 8000 available (check failed, assuming OK)")
                checks["port_8000"] = True

            progress.remove_task(task)

            # Virtual environment check
            task = progress.add_task("Checking virtual environment...", total=None)
            if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                checks["virtual_env"] = True
                progress.update(task, description="✅ Virtual environment active")
            else:
                progress.update(task, description="⚠️ No virtual environment detected")

            progress.remove_task(task)

            # Required packages check
            task = progress.add_task("Checking required packages...", total=None)
            required_packages = ["fastapi", "httpx", "uvicorn"]
            missing_packages = []

            for package in required_packages:
                try:
                    __import__(package)
                except ImportError:
                    missing_packages.append(package)

            if not missing_packages:
                checks["required_packages"] = True
                progress.update(task, description="✅ All required packages installed")
            else:
                progress.update(task, description=f"❌ Missing packages: {', '.join(missing_packages)}")

            progress.remove_task(task)

        # Display summary
        self.display_dependency_summary(checks)
        return checks

    def display_dependency_summary(self, checks: Dict[str, bool]):
        """Display dependency check summary"""
        table = Table(title="Dependency Check Summary", show_header=True, header_style="bold magenta")
        table.add_column("Component", style="dim")
        table.add_column("Status")
        table.add_column("Notes", style="italic")

        status_map = {
            "python": ("Python 3.11+", "Required for modern FastAPI"),
            "sqlite": ("SQLite Database", "For storing critics and media data"),
            "port_8000": ("Port 8000", "Default API port (configurable)"),
            "virtual_env": ("Virtual Environment", "Recommended for isolation"),
            "required_packages": ("Python Packages", "FastAPI, httpx, uvicorn")
        }

        for key, (component, note) in status_map.items():
            status = "✅ OK" if checks[key] else "❌ ISSUE"
            style = "green" if checks[key] else "red"
            table.add_row(component, f"[{style}]{status}[/{style}]", note)

        console.print(table)

        # Check if we can continue
        critical_checks = ["python", "sqlite", "required_packages"]
        critical_failures = [k for k in critical_checks if not checks[k]]

        if critical_failures:
            console.print(f"\n[red]❌ Critical dependencies missing: {', '.join(critical_failures)}[/red]")
            console.print("[yellow]Please install missing dependencies and run the wizard again.[/yellow]")
            return False

        console.print("\n[green]✅ All critical dependencies satisfied! Let's continue...[/green]")
        return True

    async def configure_jellyfin(self) -> Dict[str, Any]:
        """Interactive Jellyfin configuration"""
        console.print("\n[bold yellow]📡 Step 2: Jellyfin Configuration[/bold yellow]")

        # Get Jellyfin URL
        jellyfin_url = questionary.text(
            "Jellyfin Server URL:",
            default="http://192.168.45.181:8097",
            instruction="(Include http:// or https://)"
        ).ask()

        if not jellyfin_url:
            console.print("[red]❌ Jellyfin URL is required![/red]")
            return {}

        # Test connection
        console.print(f"\n[dim]Testing connection to {jellyfin_url}...[/dim]")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{jellyfin_url}/System/Info/Public")
                response.raise_for_status()

                server_info = response.json()
                server_name = server_info.get('ServerName', 'Unknown')
                version = server_info.get('Version', 'Unknown')

                console.print(f"[green]✅ Connected to Jellyfin server: {server_name} (v{version})[/green]")

        except Exception as e:
            console.print(f"[red]❌ Connection failed: {str(e)}[/red]")

            retry = questionary.confirm("Would you like to try a different URL?").ask()
            if retry:
                return await self.configure_jellyfin()
            else:
                console.print("[yellow]⚠️ Continuing without Jellyfin validation...[/yellow]")

        # Get API Token
        console.print("\n[dim]You need a Jellyfin API token for full functionality.[/dim]")
        console.print("[dim]Get it from: Jellyfin Admin → Dashboard → API Keys[/dim]")

        api_token = questionary.password(
            "Jellyfin API Token:",
            instruction="(Leave empty to configure later)"
        ).ask()

        if api_token:
            # Test API token
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    headers = {"X-MediaBrowser-Token": api_token}
                    response = await client.get(f"{jellyfin_url}/Users", headers=headers)
                    response.raise_for_status()

                    users = response.json()
                    console.print(f"[green]✅ API token valid! Found {len(users)} users.[/green]")

            except Exception as e:
                console.print(f"[red]❌ API token test failed: {str(e)}[/red]")
                console.print("[yellow]⚠️ You can update this later in the .env file[/yellow]")

        # Jellyfin database path (optional)
        console.print("\n[dim]Jellyfin database path is optional but enables advanced sync features.[/dim]")
        jellyfin_db_path = questionary.text(
            "Jellyfin Database Path:",
            default="/home/stilgar/docker/jellyfin-upgrade/config/data/jellyfin.db",
            instruction="(Leave empty if not available)"
        ).ask()

        return {
            "JELLYFIN_URL": jellyfin_url,
            "JELLYFIN_API_TOKEN": api_token or "",
            "JELLYFIN_DB_PATH": jellyfin_db_path or ""
        }

    async def configure_llm(self) -> Dict[str, Any]:
        """Interactive LLM configuration"""
        console.print("\n[bold yellow]🤖 Step 3: LLM Configuration[/bold yellow]")

        # Choose LLM type
        llm_type = questionary.select(
            "Which LLM system do you want to use?",
            choices=[
                "Ollama (Local - Recommended)",
                "OpenAI API (Cloud - Paid)",
                "Anthropic Claude API (Cloud - Paid)",
                "Multiple (Hybrid Setup)"
            ]
        ).ask()

        config = {}

        if "Ollama" in llm_type or "Multiple" in llm_type:
            # Configure Ollama
            ollama_url = questionary.text(
                "Ollama Server URL:",
                default="http://192.168.45.104:11434",
                instruction="(Default Ollama port is 11434)"
            ).ask()

            # Test Ollama connection and get models
            console.print(f"\n[dim]Testing Ollama connection at {ollama_url}...[/dim]")

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{ollama_url}/api/tags")
                    response.raise_for_status()

                    models_data = response.json()
                    available_models = [model["name"] for model in models_data.get("models", [])]

                    if available_models:
                        console.print(f"[green]✅ Ollama connected! Found {len(available_models)} models.[/green]")

                        # Display available models
                        table = Table(title="Available Ollama Models", show_header=True)
                        table.add_column("Model Name", style="cyan")
                        table.add_column("Size", style="dim")

                        for model in models_data.get("models", []):
                            name = model["name"]
                            size = f"{model.get('size', 0) / (1024**3):.1f}GB" if model.get('size') else "Unknown"
                            table.add_row(name, size)

                        console.print(table)

                        # Select primary model
                        primary_model = questionary.select(
                            "Select primary model:",
                            choices=available_models
                        ).ask()

                        # Select secondary model (optional)
                        remaining_models = [m for m in available_models if m != primary_model]
                        if remaining_models:
                            secondary_model = questionary.select(
                                "Select secondary model (for fallback):",
                                choices=["None"] + remaining_models
                            ).ask()

                            if secondary_model == "None":
                                secondary_model = ""
                        else:
                            secondary_model = ""

                        config.update({
                            "LLM_OLLAMA_URL": ollama_url,
                            "LLM_PRIMARY_MODEL": primary_model,
                            "LLM_SECONDARY_MODEL": secondary_model,
                        })
                    else:
                        console.print("[red]❌ No models found in Ollama![/red]")
                        console.print("[dim]Pull a model first: ollama pull qwen2:7b[/dim]")

            except Exception as e:
                console.print(f"[red]❌ Ollama connection failed: {str(e)}[/red]")
                console.print("[yellow]⚠️ Continuing with manual configuration...[/yellow]")

                # Manual model configuration
                primary_model = questionary.text(
                    "Primary model name:",
                    default="qwen3:8b"
                ).ask()

                secondary_model = questionary.text(
                    "Secondary model name (optional):",
                    default="gpt-oss:20b"
                ).ask()

                config.update({
                    "LLM_OLLAMA_URL": ollama_url,
                    "LLM_PRIMARY_MODEL": primary_model,
                    "LLM_SECONDARY_MODEL": secondary_model or "",
                })

        # Advanced LLM settings
        console.print("\n[dim]Advanced LLM Settings:[/dim]")

        timeout = questionary.text(
            "LLM timeout (seconds):",
            default="180",
            instruction="(Time to wait for model response)"
        ).ask()

        max_retries = questionary.text(
            "Max retries:",
            default="2",
            instruction="(Number of retry attempts)"
        ).ask()

        enable_fallback = questionary.confirm(
            "Enable automatic fallback between models?",
            default=True
        ).ask()

        config.update({
            "LLM_TIMEOUT": timeout,
            "LLM_MAX_RETRIES": max_retries,
            "LLM_ENABLE_FALLBACK": str(enable_fallback).lower()
        })

        return config

    def create_env_file(self, config: Dict[str, Any]) -> bool:
        """Create .env file with collected configuration"""
        console.print("\n[bold yellow]📝 Step 4: Creating Configuration File[/bold yellow]")

        try:
            import datetime

            # Load .env.example as template
            env_template = ""
            if self.env_example_file.exists():
                with open(self.env_example_file, 'r') as f:
                    env_template = f.read()

            # Create .env content
            env_content = [
                "# 🎭 Parody Critics - Environment Configuration",
                f"# Generated by Setup Wizard on {datetime.datetime.now()}",
                "",
                "# Environment",
                "PARODY_CRITICS_ENV=production",
                "",
                "# Database",
                "PARODY_CRITICS_DB_PATH=database/critics.db",
                "",
                "# Server Configuration",
                "HOST=0.0.0.0",
                "PORT=8000",
                "RELOAD=false",
                ""
            ]

            # Add collected configuration
            if config:
                for key, value in config.items():
                    if value:  # Only add non-empty values
                        env_content.append(f"{key}={value}")

            # Add default sync settings
            env_content.extend([
                "",
                "# Sync Configuration",
                "SYNC_BATCH_SIZE=100",
                "SYNC_MAX_CONCURRENT=5",
                "",
                "# Performance",
                "PARODY_CRITICS_CACHE_DURATION=300",
                "PARODY_CRITICS_LOG_LEVEL=INFO"
            ])

            # Write .env file
            with open(self.env_file, 'w') as f:
                f.write('\n'.join(env_content))

            console.print(f"[green]✅ Configuration saved to {self.env_file}[/green]")
            console.print("[dim]You can edit this file later to modify settings.[/dim]")

            return True

        except Exception as e:
            console.print(f"[red]❌ Failed to create .env file: {str(e)}[/red]")
            return False

    def setup_complete(self):
        """Display setup completion message"""
        console.print("\n[bold green]🎉 Setup Complete! 🎭[/bold green]")

        completion_text = """
Your Parody Critics installation is ready!

Next Steps:
1. Start the API server:
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

2. Access the API documentation:
   http://localhost:8000/docs

3. Test critic generation:
   curl http://localhost:8000/api/health

4. Add the JavaScript to your Jellyfin server
   (Copy frontend/parody-critics-hybrid.js)

5. Generate your first critics:
   Visit any movie in Jellyfin and enjoy! 🎬

Happy movie reviewing with Marco Aurelio and Rosario Costras! ✨
        """

        console.print(Panel(completion_text, style="bold green", expand=False))

# Main async function
async def run_setup(skip_deps: bool = False, config_only: bool = False):
    """🧙‍♂️ Interactive Setup Wizard for Parody Critics"""

    wizard = SetupWizard()

    try:
        wizard.print_header()

        # Step 1: Dependency Check
        if not skip_deps and not config_only:
            deps_ok = wizard.check_dependencies()
            if not deps_ok:
                console.print("[red]Setup cannot continue due to missing dependencies.[/red]")
                return

            # Wait for user to continue
            questionary.press_any_key_to_continue("Press any key to continue...").ask()

        # Step 2: Jellyfin Configuration
        console.print("\n[dim]Configuring Jellyfin connection...[/dim]")
        jellyfin_config = await wizard.configure_jellyfin()

        if not jellyfin_config:
            console.print("[red]❌ Jellyfin configuration failed![/red]")
            return

        # Step 3: LLM Configuration
        console.print("\n[dim]Configuring LLM system...[/dim]")
        llm_config = await wizard.configure_llm()

        # Step 4: Create .env file
        all_config = {**jellyfin_config, **llm_config}
        env_created = wizard.create_env_file(all_config)

        if not env_created:
            console.print("[red]❌ Configuration file creation failed![/red]")
            return

        # Step 5: Complete
        wizard.setup_complete()

    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Setup failed: {str(e)}[/red]")
        console.print("[dim]Please check the error and try again.[/dim]")

# CLI Interface
@click.command()
@click.option('--skip-deps', is_flag=True, help='Skip dependency checks')
@click.option('--config-only', is_flag=True, help='Only create configuration file')
def setup(skip_deps: bool, config_only: bool):
    """🧙‍♂️ Interactive Setup Wizard for Parody Critics"""
    asyncio.run(run_setup(skip_deps, config_only))

if __name__ == "__main__":
    import asyncio
    setup()