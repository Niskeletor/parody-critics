#!/usr/bin/env python3
"""
🧙‍♂️ Simple Parody Critics Setup Wizard
Simplified version for demo and testing
"""

import os
import socket
import sqlite3
import sys
from pathlib import Path

import click
import requests  # Using requests instead of httpx for simplicity
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Import logging system
from utils.logger import get_logger, setup_logging, LogTimer, log_exception

# Initialize Rich Console
console = Console()

# Setup logging for wizard (will be reconfigured in setup function if needed)
setup_logging(log_level=os.getenv('PARODY_CRITICS_LOG_LEVEL', 'INFO'))
logger = get_logger('wizard')

class SimpleSetupWizard:
    def __init__(self):
        self.config = {}
        self.project_root = Path(__file__).parent
        self.env_file = self.project_root / '.env'

    def print_header(self):
        """Display fancy wizard header"""
        logger.info("Starting Parody Critics Setup Wizard")
        header_text = """
🎭 Parody Critics Setup Wizard 🧙‍♂️
=====================================

Welcome to the interactive setup for Parody Critics!
This wizard will help you configure your system step by step.

Let's create some hilarious movie reviews together! 🎬✨
        """
        console.print(Panel(header_text, style="bold blue", expand=False))

    def check_dependencies(self) -> dict:
        """Check system dependencies and requirements"""
        logger.info("Starting dependency verification")
        console.print("\n[bold yellow]🔍 Step 1: Checking System Dependencies[/bold yellow]")

        checks = {
            "python": False,
            "sqlite": False,
            "port_8000": False,
            "virtual_env": False,
            "required_packages": False
        }

        # Python version check
        python_version = sys.version_info
        if python_version >= (3, 11):
            checks["python"] = True
            console.print(f"✅ Python {python_version.major}.{python_version.minor} detected")
        else:
            console.print(f"❌ Python {python_version.major}.{python_version.minor} - Need 3.11+")

        # SQLite check
        try:
            import sqlite3
            checks["sqlite"] = True
            console.print("✅ SQLite available")
        except ImportError:
            console.print("❌ SQLite not available")

        # Port availability check
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('localhost', 8000))
                if result != 0:  # Port is free
                    checks["port_8000"] = True
                    console.print("✅ Port 8000 available")
                else:
                    console.print("⚠️ Port 8000 in use (can be configured)")
                    checks["port_8000"] = True
        except Exception:
            console.print("✅ Port 8000 available (assuming OK)")
            checks["port_8000"] = True

        # Virtual environment check
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            checks["virtual_env"] = True
            console.print("✅ Virtual environment active")
        else:
            console.print("⚠️ No virtual environment detected")

        # Required packages check
        required_packages = ["fastapi", "httpx", "uvicorn"]
        missing_packages = []

        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)

        if not missing_packages:
            checks["required_packages"] = True
            console.print("✅ All required packages installed")
        else:
            console.print(f"❌ Missing packages: {', '.join(missing_packages)}")

        # Display summary table
        self.display_dependency_summary(checks)
        return checks

    def display_dependency_summary(self, checks: dict):
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
            logger.error(f"Critical dependencies missing: {', '.join(critical_failures)}")
            logger.error("Cannot proceed with setup - missing critical requirements")
            console.print(f"\n[red]❌ Critical dependencies missing: {', '.join(critical_failures)}[/red]")
            console.print("[yellow]Please install missing dependencies and run the wizard again.[/yellow]")
            return False

        console.print("\n[green]✅ All critical dependencies satisfied![/green]")
        return True

    def test_jellyfin_connection(self, url: str, api_token: str = "") -> dict:
        """Test Jellyfin connection"""
        logger.info(f"Testing Jellyfin connection to: {url}")
        console.print(f"\n[dim]Testing connection to {url}...[/dim]")

        try:
            with LogTimer(logger, f"Jellyfin connection test to {url}"):
                # Test basic connection
                response = requests.get(f"{url}/System/Info/Public", timeout=10)
                response.raise_for_status()

                server_info = response.json()
                server_name = server_info.get('ServerName', 'Unknown')
                version = server_info.get('Version', 'Unknown')

                logger.info(f"Successfully connected to Jellyfin: {server_name} v{version}")
                console.print(f"[green]✅ Connected to Jellyfin server: {server_name} (v{version})[/green]")

                # Test API token if provided
                if api_token:
                    logger.debug("Testing API token validity")
                    headers = {"X-MediaBrowser-Token": api_token}
                    response = requests.get(f"{url}/Users", headers=headers, timeout=10)
                    response.raise_for_status()

                    users = response.json()
                    logger.info(f"API token valid - found {len(users)} users")
                    console.print(f"[green]✅ API token valid! Found {len(users)} users.[/green]")

                return {"success": True, "server_name": server_name, "version": version}

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Jellyfin connection failed - network error: {str(e)}")
            console.print(f"[red]❌ Connection failed: Cannot reach server at {url}[/red]")
            return {"success": False, "error": f"Network error: {str(e)}"}
        except requests.exceptions.Timeout as e:
            logger.error(f"Jellyfin connection timeout after 10s: {str(e)}")
            console.print(f"[red]❌ Connection timeout: Server took too long to respond[/red]")
            return {"success": False, "error": f"Timeout: {str(e)}"}
        except requests.exceptions.HTTPError as e:
            logger.error(f"Jellyfin HTTP error: {e.response.status_code} - {str(e)}")
            console.print(f"[red]❌ HTTP error {e.response.status_code}: {str(e)}[/red]")
            return {"success": False, "error": f"HTTP {e.response.status_code}: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error during Jellyfin connection test: {str(e)}")
            log_exception(logger, e, "Jellyfin connection test")
            console.print(f"[red]❌ Connection failed: {str(e)}[/red]")
            return {"success": False, "error": str(e)}

    def test_ollama_connection(self, url: str) -> dict:
        """Test Ollama connection and get models"""
        logger.info(f"Testing Ollama connection to: {url}")
        console.print(f"\n[dim]Testing Ollama connection at {url}...[/dim]")

        try:
            with LogTimer(logger, f"Ollama connection test to {url}"):
                response = requests.get(f"{url}/api/tags", timeout=10)
                response.raise_for_status()

                models_data = response.json()
                available_models = [model["name"] for model in models_data.get("models", [])]

                if available_models:
                    logger.info(f"Successfully connected to Ollama - found {len(available_models)} models: {', '.join(available_models)}")
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

                    return {"success": True, "models": available_models}
                else:
                    logger.warning("Ollama connection successful but no models found")
                    console.print("[red]❌ No models found in Ollama![/red]")
                    console.print("[dim]Pull a model first: ollama pull qwen2:7b[/dim]")
                    return {"success": False, "error": "No models found"}

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ollama connection failed - network error: {str(e)}")
            console.print(f"[red]❌ Ollama connection failed: Cannot reach server at {url}[/red]")
            return {"success": False, "error": f"Network error: {str(e)}"}
        except requests.exceptions.Timeout as e:
            logger.error(f"Ollama connection timeout after 10s: {str(e)}")
            console.print(f"[red]❌ Connection timeout: Ollama server took too long to respond[/red]")
            return {"success": False, "error": f"Timeout: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error during Ollama connection test: {str(e)}")
            log_exception(logger, e, "Ollama connection test")
            console.print(f"[red]❌ Ollama connection failed: {str(e)}[/red]")
            return {"success": False, "error": str(e)}

    def demo_config(self) -> dict:
        """Demo configuration with pre-filled values"""
        console.print("\n[bold yellow]📝 Demo Configuration (Pre-filled values)[/bold yellow]")

        config = {
            "JELLYFIN_URL": "http://192.168.45.181:8097",
            "JELLYFIN_API_TOKEN": "demo-api-token",
            "LLM_OLLAMA_URL": "http://192.168.45.104:11434",
            "LLM_PRIMARY_MODEL": "qwen3:8b",
            "LLM_SECONDARY_MODEL": "gpt-oss:20b",
            "LLM_TIMEOUT": "180",
            "LLM_MAX_RETRIES": "2",
            "LLM_ENABLE_FALLBACK": "true"
        }

        console.print("\n[cyan]Demo Configuration Values:[/cyan]")
        for key, value in config.items():
            console.print(f"  {key}: [green]{value}[/green]")

        return config

    def interactive_config(self) -> dict:
        """Interactive configuration with simple prompts"""
        console.print("\n[bold yellow]📝 Interactive Configuration[/bold yellow]")

        config = {}

        # Jellyfin URL
        console.print("\n[cyan]Jellyfin Configuration:[/cyan]")
        jellyfin_url = input("Jellyfin Server URL [http://192.168.45.181:8097]: ").strip()
        if not jellyfin_url:
            jellyfin_url = "http://192.168.45.181:8097"

        config["JELLYFIN_URL"] = jellyfin_url

        # Test Jellyfin connection
        jellyfin_test = self.test_jellyfin_connection(jellyfin_url)

        # API Token (optional)
        api_token = input("Jellyfin API Token (optional, press Enter to skip): ").strip()
        if api_token:
            config["JELLYFIN_API_TOKEN"] = api_token
            # Test API token
            self.test_jellyfin_connection(jellyfin_url, api_token)

        # Jellyfin DB Path
        jellyfin_db = input("Jellyfin Database Path (optional, press Enter to skip): ").strip()
        if jellyfin_db:
            config["JELLYFIN_DB_PATH"] = jellyfin_db

        # LLM Configuration
        console.print("\n[cyan]LLM Configuration:[/cyan]")
        ollama_url = input("Ollama Server URL [http://192.168.45.104:11434]: ").strip()
        if not ollama_url:
            ollama_url = "http://192.168.45.104:11434"

        config["LLM_OLLAMA_URL"] = ollama_url

        # Test Ollama connection
        ollama_test = self.test_ollama_connection(ollama_url)

        if ollama_test.get("success"):
            models = ollama_test.get("models", [])
            console.print(f"\nAvailable models: {', '.join(models)}")

            primary_model = input(f"Primary model [{models[0] if models else 'qwen3:8b'}]: ").strip()
            if not primary_model:
                primary_model = models[0] if models else 'qwen3:8b'
            config["LLM_PRIMARY_MODEL"] = primary_model

            if len(models) > 1:
                secondary_model = input(f"Secondary model (fallback) [{models[1] if len(models) > 1 else 'gpt-oss:20b'}]: ").strip()
                if not secondary_model and len(models) > 1:
                    secondary_model = models[1]
                elif not secondary_model:
                    secondary_model = "gpt-oss:20b"
                config["LLM_SECONDARY_MODEL"] = secondary_model
        else:
            # Manual configuration
            config["LLM_PRIMARY_MODEL"] = input("Primary model name [qwen3:8b]: ").strip() or "qwen3:8b"
            config["LLM_SECONDARY_MODEL"] = input("Secondary model name [gpt-oss:20b]: ").strip() or "gpt-oss:20b"

        # LLM Settings
        config["LLM_TIMEOUT"] = input("LLM timeout in seconds [180]: ").strip() or "180"
        config["LLM_MAX_RETRIES"] = input("Max retries [2]: ").strip() or "2"
        config["LLM_ENABLE_FALLBACK"] = input("Enable fallback [true]: ").strip() or "true"

        return config

    def create_env_file(self, config: dict) -> bool:
        """Create .env file with collected configuration"""
        logger.info(f"Creating .env configuration file at: {self.env_file}")
        console.print("\n[bold yellow]📝 Creating Configuration File[/bold yellow]")

        try:
            with LogTimer(logger, "Creating .env configuration file"):
                import datetime

                # Log config summary
                config_summary = {k: v for k, v in config.items() if not k.endswith('_TOKEN')}  # Don't log sensitive data
                logger.debug(f"Configuration summary: {config_summary}")

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
                added_configs = []
                for key, value in config.items():
                    if value:  # Only add non-empty values
                        env_content.append(f"{key}={value}")
                        added_configs.append(key)

                logger.debug(f"Added configuration keys: {added_configs}")

                # Add default settings
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
                with open(self.env_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(env_content))

                logger.info(f"Successfully created .env file with {len(added_configs)} configuration entries")
                console.print(f"[green]✅ Configuration saved to {self.env_file}[/green]")
                return True

        except PermissionError as e:
            logger.error(f"Permission denied creating .env file: {str(e)}")
            console.print(f"[red]❌ Permission denied: Cannot write to {self.env_file}[/red]")
            return False
        except FileNotFoundError as e:
            logger.error(f"Directory not found for .env file: {str(e)}")
            console.print(f"[red]❌ Directory not found: {self.env_file.parent}[/red]")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating .env file: {str(e)}")
            log_exception(logger, e, ".env file creation")
            console.print(f"[red]❌ Failed to create .env file: {str(e)}[/red]")
            return False

    def setup_complete(self):
        """Display setup completion message"""
        logger.info("Setup wizard completed successfully")
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

5. Generate your first critics and enjoy! 🎬

Happy movie reviewing with Marco Aurelio and Rosario Costras! ✨
        """

        console.print(Panel(completion_text, style="bold green", expand=False))

@click.command()
@click.option('--skip-deps', is_flag=True, help='Skip dependency checks')
@click.option('--config-only', is_flag=True, help='Only create configuration file')
@click.option('--demo', is_flag=True, help='Run demo mode with pre-filled values')
@click.option('--debug', is_flag=True, help='Enable DEBUG logging level')
@click.option('--log-info', is_flag=True, help='Show logging system information')
def setup(skip_deps: bool, config_only: bool, demo: bool, debug: bool, log_info: bool):
    """🧙‍♂️ Interactive Setup Wizard for Parody Critics"""

    # Reconfigure logging if debug is enabled
    if debug:
        global logger
        setup_logging(log_level='DEBUG')
        logger = get_logger('wizard')
        logger.debug("DEBUG logging enabled via --debug flag")

    # Show logging information if requested
    if log_info:
        from utils.logger import _global_logger
        if _global_logger:
            log_debug_info = _global_logger.get_debug_info()

            console.print("\n[bold blue]🔍 Logging System Information[/bold blue]")
            info_table = Table(show_header=True, header_style="bold magenta")
            info_table.add_column("Property", style="cyan")
            info_table.add_column("Value", style="green")

            info_table.add_row("Logger Name", log_debug_info['logger_name'])
            info_table.add_row("Log Level", log_debug_info['log_level'])
            info_table.add_row("Log Directory", log_debug_info['log_directory'])
            info_table.add_row("Handlers Count", str(log_debug_info['handlers_count']))
            info_table.add_row("Rich Available", str(log_debug_info['rich_available']))
            info_table.add_row("Log Files", f"{len(log_debug_info['log_files'])} files")

            console.print(info_table)

            if log_debug_info['log_files']:
                console.print("\n[dim]Available log files:[/dim]")
                for log_file in log_debug_info['log_files']:
                    console.print(f"  📄 {log_file}")

            console.print("\n[dim]Use --debug for detailed logging output[/dim]")
            return

    logger.info(f"Starting setup wizard - skip_deps={skip_deps}, config_only={config_only}, demo={demo}, debug={debug}")
    wizard = SimpleSetupWizard()

    try:
        with LogTimer(logger, "Complete setup wizard execution"):
            wizard.print_header()

            # Step 1: Dependency Check
            if not skip_deps and not config_only:
                logger.info("Starting dependency verification phase")
                deps_ok = wizard.check_dependencies()
                if not deps_ok:
                    logger.error("Setup aborted - dependency verification failed")
                    console.print("[red]Setup cannot continue due to missing dependencies.[/red]")
                    return

                if not demo:
                    input("\nPress Enter to continue...")

            # Step 2: Configuration
            logger.info("Starting configuration phase")
            if demo:
                logger.info("Using demo configuration mode")
                config = wizard.demo_config()
            else:
                logger.info("Using interactive configuration mode")
                config = wizard.interactive_config()

            # Step 3: Create .env file
            logger.info("Starting environment file creation phase")
            env_created = wizard.create_env_file(config)

            if not env_created:
                logger.error("Setup failed - could not create .env file")
                console.print("[red]❌ Configuration file creation failed![/red]")
                return

            # Step 4: Complete
            logger.info("Setup wizard completed successfully")
            wizard.setup_complete()

    except KeyboardInterrupt:
        logger.warning("Setup cancelled by user (Ctrl+C)")
        console.print("\n[yellow]Setup cancelled by user.[/yellow]")
    except Exception as e:
        logger.error(f"Setup wizard failed with unexpected error: {str(e)}")
        log_exception(logger, e, "Setup wizard execution")
        console.print(f"\n[red]Setup failed: {str(e)}[/red]")
        console.print("[dim]Please check the error and try again.[/dim]")
        console.print(f"[dim]Check logs for details: {wizard.project_root}/logs/parody_critics.log[/dim]")

if __name__ == "__main__":
    setup()