from __future__ import annotations

import ipaddress
import socket
from typing import Any

import psutil


def get_ethernet_interface_records() -> list[dict[str, Any]]:
    """Return active, non-loopback IPv4 addresses on Ethernet/LAN adapters only."""
    records: list[dict[str, Any]] = []
    addresses_by_interface = psutil.net_if_addrs()
    stats_by_interface = psutil.net_if_stats()

    for interface_name, addresses in addresses_by_interface.items():
        folded_name = interface_name.casefold()
        if not any(token in folded_name for token in ("ethernet", "eth", "lan")):
            continue

        stats = stats_by_interface.get(interface_name)
        if stats is None or not stats.isup:
            continue

        ipv4_addresses: list[str] = []
        mac_address: str | None = None
        for address in addresses:
            if address.family == socket.AF_INET:
                raw_ip = address.address.split("%", 1)[0]
                try:
                    parsed = ipaddress.IPv4Address(raw_ip)
                except ipaddress.AddressValueError:
                    continue
                if parsed.is_loopback or parsed.is_link_local or parsed.is_unspecified:
                    continue
                if raw_ip not in ipv4_addresses:
                    ipv4_addresses.append(raw_ip)
            elif address.family == getattr(psutil, "AF_LINK", object()):
                candidate = (address.address or "").strip()
                if candidate and candidate not in {"00:00:00:00:00:00", "00-00-00-00-00-00"}:
                    mac_address = candidate

        for ip_address in ipv4_addresses:
            records.append({
                "interface_name": interface_name,
                "interface_type": "Ethernet",
                "ip_address": ip_address,
                "mac_address": mac_address,
                "is_active": True,
            })

    return sorted(records, key=lambda item: (item["interface_name"].casefold(), item["ip_address"]))


def get_ethernet_ipv4_addresses() -> list[str]:
    return [item["ip_address"] for item in get_ethernet_interface_records()]
