import requests
import logging

logger = logging.getLogger("DuckDNS.IPUtils")

def get_ipv4():
    """Get the public IPv4 address using external services."""
    services = [
        "https://api.ipify.org",
        "https://ipv4.icanhazip.com",
        "https://v4.ident.me",
    ]
    
    for service in services:
        try:
            response = requests.get(service, timeout=5)
            if response.status_code == 200:
                ip = response.text.strip()
                logger.info(f"Retrieved IPv4 address: {ip}")
                return ip
        except Exception as e:
            logger.warning(f"Failed to get IPv4 from {service}: {str(e)}")
    
    logger.error("Failed to retrieve IPv4 address from any service")
    return None

def get_ipv6():
    """Get the public IPv6 address using external services."""
    services = [
        "https://api6.ipify.org",
        "https://ipv6.icanhazip.com",
        "https://v6.ident.me",
    ]
    
    for service in services:
        try:
            response = requests.get(service, timeout=5)
            if response.status_code == 200:
                ip = response.text.strip()
                logger.info(f"Retrieved IPv6 address: {ip}")
                return ip
        except Exception as e:
            logger.debug(f"Failed to get IPv6 from {service}: {str(e)}")
    
    logger.warning("No IPv6 address detected")
    return None