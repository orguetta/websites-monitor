# Standard library imports
from datetime import datetime
import logging
from typing import List, Tuple, Callable, Optional
import sys
import asyncio
import yaml
from dataclasses import dataclass
import os


# Import all check functions
from checks.check_domain_breach import check_domain_breach
from checks.check_domain_expiration import check_domain_expiration
from checks.check_ssl_cert import check_ssl_cert
from checks.check_dns_blacklist import check_dns_blacklist
from checks.check_domainsblacklists_blacklist import check_domainsblacklists_blacklist
from checks.check_hsts import check_hsts
from checks.check_xss_protection import check_xss_protection
from checks.check_redirect_chains import check_redirect_chains
from checks.check_pagespeed_performances import check_pagespeed_performances
from checks.check_website_load_time import check_website_load_time
from checks.check_rate_limiting import check_rate_limiting
from checks.check_cdn import check_cdn
from checks.check_brotli_compression import check_brotli_compression
from checks.check_deprecated_libraries import check_deprecated_libraries
from checks.check_clientside_rendering import check_clientside_rendering
from checks.check_mixed_content import check_mixed_content
from checks.check_content_type_headers import check_content_type_headers
from checks.check_internationalization import check_internationalization
from checks.check_floc import check_floc
from checks.check_amp_compatibility import check_amp_compatibility
from checks.check_robot_txt import check_robot_txt
from checks.check_sitemap import check_sitemap
from checks.check_favicon import check_favicon
from checks.check_alt_tags import check_alt_tags
from checks.check_open_graph_protocol import check_open_graph_protocol
from checks.check_semantic_markup import check_semantic_markup
from checks.check_ad_and_tracking import check_ad_and_tracking
from checks.check_privacy_protected_whois import check_privacy_protected_whois
from checks.check_privacy_exposure import check_privacy_exposure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration class to store all settings."""
    websites: List[str]
    output_file: str = "README.md"
    max_workers: int = 4
    timeout: int = 30
    log_file: str = "monitor.log"
    report_template: str = "report_template.md"
    github_workflow_badge: str = "https://github.com/fabriziosalmi/websites-monitor/actions/workflows/create-report.yml/badge.svg"
    pagespeed_api_key: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """Create a Config instance from a dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class WebsiteMonitor:
    def __init__(self, config: Config):
        self.config = config
        self.error_log = []
        self.check_functions = self._initialize_check_functions()

    class Check:
        """Represents a single website check."""
        def __init__(self, name: str, function: Callable, enabled: bool = True, timeout: Optional[int] = None):
            self.name = name
            self.function = function
            self.enabled = enabled
            self.timeout = timeout

        async def execute(self, website: str, config: Config, default_timeout: int) -> str:
            """Execute the check with timeout handling."""
            try:
                if self.name == "Pagespeed" and asyncio.iscoroutinefunction(self.function):
                  return await asyncio.wait_for(self.function(website, api_key=config.pagespeed_api_key), self.timeout or default_timeout)
                elif self.name == "Pagespeed":
                  return self.function(website, api_key=config.pagespeed_api_key)
                elif self.name == "Rate Limiting":
                   return self.function(f"https://{website}")
                elif asyncio.iscoroutinefunction(self.function):
                  return await asyncio.wait_for(self.function(website), self.timeout or default_timeout)
                else:
                   return self.function(website)
            except asyncio.TimeoutError:
                logger.warning(f"Check {self.name} for {website} timed out.")
                return "🔴"  # Timeout indicator
            except Exception as e:
                logger.error(f"Check {self.name} failed for {website}: {e}")
                return "⚪"  # Error indicator

    def _initialize_check_functions(self) -> List['WebsiteMonitor.Check']:
        """Initialize the list of check functions with their names."""
        checks = [
            self.Check("Domain breach", check_domain_breach),
            self.Check("Domain Expiration", check_domain_expiration),
            self.Check("SSL Certificate", check_ssl_cert),
            self.Check("DNS Blacklists", check_dns_blacklist, timeout=45),
            self.Check("DomainsBlacklists", check_domainsblacklists_blacklist),
            self.Check("HSTS", check_hsts),
            self.Check("XSS Protection", check_xss_protection),
            self.Check("Redirect chains", check_redirect_chains),
            self.Check("Pagespeed", check_pagespeed_performances, timeout=60),
            self.Check("Load Time", check_website_load_time),
            self.Check("Rate Limiting", check_rate_limiting),
            self.Check("CDN", check_cdn),
            self.Check("Brotli", check_brotli_compression),
            self.Check("Deprecated Libraries", check_deprecated_libraries),
            self.Check("Client Rendering", check_clientside_rendering),
            self.Check("Mixed Content", check_mixed_content),
            self.Check("Content-Type", check_content_type_headers),
            self.Check("i18n", check_internationalization),
            self.Check("FLoC", check_floc),
            self.Check("AMP", check_amp_compatibility),
            self.Check("Robots.txt", check_robot_txt),
            self.Check("Sitemap", check_sitemap),
            self.Check("Favicon", check_favicon),
            self.Check("Alt Tags", check_alt_tags),
            self.Check("Open Graph", check_open_graph_protocol),
            self.Check("Semantic Markup", check_semantic_markup),
            self.Check("Ad Tracking", check_ad_and_tracking),
            self.Check("WHOIS Privacy", check_privacy_protected_whois),
            self.Check("Privacy Exposure", check_privacy_exposure),
        ]
        return [check for check in checks if check.enabled]


class PerformanceMonitor:
    """Tracks execution time and performance metrics."""
    def __init__(self):
        self.start_time = None
        self.end_time = None
        
    def start(self):
        """Start monitoring."""
        self.start_time = datetime.now()
        
    def stop(self):
        """Stop monitoring."""
        self.end_time = datetime.now()
        
    def get_summary(self) -> dict:
        """Get performance summary."""
        if not self.start_time or not self.end_time:
            return {}
        return {
            "total_duration": (self.end_time - self.start_time).total_seconds()
        }

def generate_report(config: Config, check_results: List[Tuple[str, List[str]]]):
    """Generates the markdown report."""
    
    with open(config.report_template, "r") as f:
        report_template = f.read()
        
    # Initialize the report content
    report_content = f"""{report_template}
[![GitHub Workflow Status]({config.github_workflow_badge})]

## Website Monitor Report

This report was automatically generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}.

| Website | {' | '.join([check_name for check_name, _ in check_results])} |
|---------|{'|'.join(['---' for _ in check_results])}|
"""

    # Add results for each website
    for website in config.websites:
        row = [website]
        for _, results in check_results:
            result_index = config.websites.index(website)
            row.append(str(results[result_index]))
        report_content += " | ".join(row) + " |\n"
        
    
    with open(config.output_file, "w") as f:
        f.write(report_content)


async def main():
    """Main execution function."""
    performance_monitor = PerformanceMonitor()
    performance_monitor.start()
    try:
        # Load configuration
        config = load_config()
        monitor = WebsiteMonitor(config)

        # Run all checks
        check_results = []
        for check in monitor.check_functions:
            results = []
            for website in config.websites:
                result = await check.execute(website, config, config.timeout)
                results.append(result)
            check_results.append((check.name, results))

        logger.info("All checks completed successfully.")
        
        generate_report(config, check_results)
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)

    performance_monitor.stop()
    logger.info(f"Execution completed in {performance_monitor.get_summary()['total_duration']} seconds.")


def load_config(config_file: str = 'config.yaml') -> Config:
    """Load configuration from YAML file."""
    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        # Get the API key from the environment variable if set
        api_key = os.environ.get('PAGESPEED_API_KEY')
        if api_key:
            config_data['pagespeed_api_key'] = api_key
        return Config.from_dict(config_data)
    except FileNotFoundError:
        logger.warning("Config file not found. Falling back to default configuration.")
        return Config(websites=["example.com"])


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
