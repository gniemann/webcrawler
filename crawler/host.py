
import re


# regex to match just the host (including leading http...)
host_regex = re.compile(r'''https?://([a-z0-9\-]+\.){1,}[a-z0-9]+''', re.IGNORECASE)

def get_host(url):
    """Extracts and returns just the service + host from url"""
    return host_regex.match(url).group()