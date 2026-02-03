import typer
from typing import Optional
from pathlib import Path
from .pagodo import Pagodo
from .scraper import retrieve_google_dorks, categories
from .config import load_config, ensure_config_exists, CONFIG_PATH
from .connectors.serper import SerperConnector
from .connectors.serpapi import SerpApiConnector

app = typer.Typer(help="pagodo - Passive Google Dork")

# Load config once on module level or inside commands. 
# Module level is easier for Typer defaults but config file might not exist yet.
# To support auto-init, we should checking/creating at the start.
# However, implicit creation on import is bad practice.
# We will do it in a callback or at the start of commands.

def get_config_or_default(key: str, default: any) -> any:
    """Helper to get config value or default."""
    config = load_config()
    return config.get(key, default)

@app.callback()
def main(ctx: typer.Context):
    """
    Pagodo - Passive Google Dork
    
    Configuration file: ~/.config/pagodo.yml
    """
    # Ensure config exists on first run
    if ensure_config_exists():
        typer.echo(f"Created default configuration file at {CONFIG_PATH}")

@app.command()
def scan(
    google_dorks_file: str = typer.Option(None, "-g", "--google-dorks-file", help="File containing Google dorks, 1 per line."),
    domain: str = typer.Option(None, "-d", "--domain", help="Domain to scope the Google dork searches."),
    minimum_delay: int = typer.Option(None, "-i", "--minimum-delay", help="Minimum delay (in seconds) between a Google dork search."),
    maximum_delay: int = typer.Option(None, "-x", "--maximum-delay", help="Maximum delay (in seconds) between a Google dork search."),
    disable_ssl_verification: bool = typer.Option(None, "-l", "--disable-ssl-verification", help="Disable SSL/TLS validation."),
    max_search_result_urls_to_return_per_dork: int = typer.Option(None, "-m", "--max-urls", help="Maximum results to return per dork."),
    json_results_file: Optional[str] = typer.Option(None, "-o", "--json-file", help="Save URL dork data to a JSON file."),
    text_results_file: Optional[str] = typer.Option(None, "-s", "--text-file", help="Save URL dork data to a text file."),
    verbosity: int = typer.Option(None, "-v", "--verbosity", help="Verbosity level (0=NOTSET, 1=CRITICAL, 2=ERROR, 3=WARNING, 4=INFO, 5=DEBUG)."),
    specific_log_file_name: str = typer.Option(None, "-z", "--log", help="Save log data to a specific log filename."),
    country_code: str = typer.Option(None, "-c", "--country-code", help="Country code to use for the Google search results."),
    max_results_per_search: int = typer.Option(None, "-n", "--max-results-per-search", help="Maximum results to return per search request (max 100)."),
    serper_api_key: str = typer.Option(None, "--api-key", help="API Key for the selected engine"),
    engine: str = typer.Option(None, "--engine", help="Search engine connector to use (default: serper)."),
    max_workers: int = typer.Option(None, "-w", "--workers", help="Number of concurrent threads to use (default: 4)."),
):
    """
    Perform Google dork searches.
    """
    config = load_config()
    
    # Resolve values: CLI arg > Config > Default
    # Note: Typer defaults are None here so we can distinguish if user provided flag.
    
    # Defaults (hardcoded fallbacks if config is missing or empty)
    defaults = {
        "dorks_dir": str(Path.home() / ".local" / "share" / "pagodo" / "dorks"),
        "google_dorks_file": str(Path.home() / ".local" / "share" / "pagodo" / "dorks" / "all_google_dorks.txt"),
        "domain": "",
        "minimum_delay": 1,
        "maximum_delay": 2,
        "disable_ssl_verification": False,
        "max_urls": 100,
        "verbosity": 4,
        "specific_log_file_name": None,
        "country_code": "vn",
        "max_results_per_search": 100,
        "serper_api_key": None,
        "serpapi_api_key": None,
        "engine": "serper",
        "max_workers": 4
    }
    
    # Helper to resolve
    def resolve(arg_val, config_key, default_val):
        if arg_val is not None:
            return arg_val
        if config_key in config:
            return config[config_key]
        return default_val

    # Resolve arguments
    # ... (dorks file resolution logic is fine) ...
    
    final_dorks_file = resolve(google_dorks_file, "google_dorks_file", "dorks/all_google_dorks.txt")
    if final_dorks_file == "dorks/all_google_dorks.txt" and "dorks_dir" in config:
         final_dorks_file = str(Path(config["dorks_dir"]) / "all_google_dorks.txt")
         
    # If explicitly set in defaults (it is now), use that.
    if google_dorks_file is None and "google_dorks_file" in config:
        final_dorks_file = config["google_dorks_file"]
    elif google_dorks_file is None:
        # Fallback to the hardcoded default in cli if config missing
        final_dorks_file = defaults["google_dorks_file"]
    else:
        final_dorks_file = google_dorks_file
    
    # Engine resolution
    final_engine = resolve(engine, "engine", "serper")
    
    client = None
    if final_engine == "serper":
        final_api_key = resolve(serper_api_key, "serper_api_key", None)
        # We rely on env vars if not passed, but SerperConnector checks explicitly? 
        # Actually SerperConnector doesn't check defaults, Pagodo used to.
        # So we should check env var here if final_api_key is still None
        if not final_api_key:
             import os
             final_api_key = os.getenv("SERPER_API_KEY")
             
        if not final_api_key:
             typer.echo("Error: Serper API key not found. Please provide it via --api-key, config file, or SERPER_API_KEY environment variable.", err=True)
             raise typer.Exit(code=1)
             
        client = SerperConnector(api_key=final_api_key)
    elif final_engine == "serpapi":
        # Resolve SerpApi Key
        # If --api-key passed, it overrides everything for the selected engine.
        # Otherwise check key-specific config/env
        final_api_key = resolve(serper_api_key, "serpapi_api_key", None)
        
        if not final_api_key:
             import os
             final_api_key = os.getenv("SERPAPI_API_KEY")
             
        if not final_api_key:
             typer.echo("Error: SerpApi API key not found. Please provide it via --api-key, config file (serpapi_api_key), or SERPAPI_API_KEY environment variable.", err=True)
             raise typer.Exit(code=1)
             
        client = SerpApiConnector(api_key=final_api_key)
    else:
        typer.echo(f"Error: Unknown engine '{final_engine}'. Supported engines: serper, serpapi", err=True)
        raise typer.Exit(code=1)

    # Pagodo class expects strict types, so ensure we cast if compatible or rely on python dynamic typing
    pagodo = Pagodo(
        google_dorks_file=final_dorks_file,
        domain=resolve(domain, "domain", ""),
        max_search_result_urls_to_return_per_dork=resolve(max_search_result_urls_to_return_per_dork, "max_urls", 100),
        save_pagodo_results_to_json_file=json_results_file if json_results_file is not None else False, # Keep manual flag for now
        save_urls_to_file=text_results_file if text_results_file is not None else False,
        minimum_delay_between_dork_searches_in_seconds=resolve(minimum_delay, "minimum_delay", 1),
        maximum_delay_between_dork_searches_in_seconds=resolve(maximum_delay, "maximum_delay", 2),
        disable_verify_ssl=resolve(disable_ssl_verification, "disable_ssl_verification", False),
        verbosity=resolve(verbosity, "verbosity", 4),
        specific_log_file_name=resolve(specific_log_file_name, "specific_log_file_name", None),
        country_code=resolve(country_code, "country_code", "vn"),
        max_results_per_search=resolve(max_results_per_search, "max_results_per_search", 100),
        client=client,
        max_workers=resolve(max_workers, "max_workers", 4)
    )
    pagodo.go()

@app.command()
def scrape(
    save_json: bool = typer.Option(False, "-j", "--json", help="Save GHDB json response to all_google_dorks.json"),
    save_txt: bool = typer.Option(False, "-s", "--txt", help="Save all the Google dorks to all_google_dorks.txt"),
    save_categories: bool = typer.Option(False, "-i", "--individual", help="Write all the individual dork categories types to separate files."),
    dorks_dir: str = typer.Option(None, "--dir", help="Directory to save dorks files."),
):
    """
    Retrieve Google Hacking Database dorks.
    """
    config = load_config()
    final_dorks_dir = dorks_dir
    if final_dorks_dir is None:
        final_dorks_dir = config.get("dorks_dir", str(Path.home() / ".local" / "share" / "pagodo" / "dorks"))
    
    retrieve_google_dorks(
        save_json_response_to_file=save_json,
        save_all_dorks_to_file=save_txt,
        save_individual_categories_to_files=save_categories,
        dorks_dir=final_dorks_dir
    )

@app.command()
def list_categories():
    """
    List available dork categories.
    """
    import json
    print(json.dumps(categories, indent=4))
    
@app.command()
def init():
    """
    Initialize the configuration file.
    """
    if ensure_config_exists():
        typer.echo(f"Created default configuration file at {CONFIG_PATH}")
    else:
        typer.echo(f"Configuration file already exists at {CONFIG_PATH}")

if __name__ == "__main__":
    app()
