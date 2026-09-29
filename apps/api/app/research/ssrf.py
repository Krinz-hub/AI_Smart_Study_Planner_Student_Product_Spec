import ipaddress
import socket
from urllib.parse import urlparse
from app.common.errors import InvalidRequestException, ForbiddenException


BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback IPv4
    ipaddress.ip_network("10.0.0.0/8"),       # Private RFC1918
    ipaddress.ip_network("172.16.0.0/12"),    # Private RFC1918
    ipaddress.ip_network("192.168.0.0/16"),   # Private RFC1918
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local / Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("::1/128"),          # Loopback IPv6
    ipaddress.ip_network("fc00::/7"),         # Unique local IPv6
    ipaddress.ip_network("fe80::/10"),        # Link-local IPv6
]

FORBIDDEN_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
    "metadata.local",
}


def validate_safe_url(url: str) -> str:
    """
    Validates URL to strictly prevent Server-Side Request Forgery (SSRF).
    Blocks private IP ranges, loopback, cloud metadata endpoints, and non-HTTP protocols.
    """
    if not url or not isinstance(url, str):
        raise InvalidRequestException("URL must be provided")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ForbiddenException("Only HTTP and HTTPS protocols are permitted")

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise InvalidRequestException("Invalid URL: missing hostname")

    if hostname in FORBIDDEN_HOSTNAMES or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise ForbiddenException(f"SSRF Protection: Access to internal host '{hostname}' is blocked")

    # Resolve IP address to detect DNS rebinding or direct IP requests
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        ips = [ai[4][0] for ai in addr_info]
    except socket.gaierror:
        # If hostname cannot be resolved, allow or raise invalid
        raise InvalidRequestException(f"Unable to resolve hostname '{hostname}'")

    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
            for net in BLOCKED_NETWORKS:
                if ip in net:
                    raise ForbiddenException(
                        f"SSRF Protection: URL resolves to forbidden/private IP address {ip_str}"
                    )
        except ValueError:
            continue

    return url
