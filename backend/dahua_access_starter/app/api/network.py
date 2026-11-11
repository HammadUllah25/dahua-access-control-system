from __future__ import annotations

from fastapi import APIRouter

from app.services.network_interfaces import get_ethernet_interface_records

router = APIRouter(prefix="/api/network", tags=["Network"])


@router.get("/interfaces")
def list_network_interfaces():
    """List active Ethernet/LAN IPv4 adapters available to this backend host."""
    return get_ethernet_interface_records()
