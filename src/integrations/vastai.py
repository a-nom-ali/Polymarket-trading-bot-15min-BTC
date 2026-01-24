"""
Vast.ai GPU Marketplace Integration

Production implementation of Vast.ai API client for GPU rental optimization.

API Documentation: https://docs.vast.ai/api-reference/
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GPUOffer:
    """Represents a GPU rental offer from Vast.ai"""

    # Identification
    offer_id: int
    machine_id: int
    host_id: int

    # GPU specs
    gpu_name: str
    num_gpus: int
    gpu_ram: int  # MB per GPU
    gpu_total_ram: int  # Total MB across all GPUs
    gpu_arch: str  # nvidia, amd

    # Pricing ($/hour)
    dph_base: float  # Base price
    dph_total: float  # Total price including storage/bandwidth
    discounted_dph_total: Optional[float] = None

    # Performance
    dlperf: Optional[float] = None  # Deep learning performance score
    dlperf_per_dphtotal: Optional[float] = None  # Performance per dollar
    compute_cap: Optional[int] = None  # CUDA compute capability

    # Infrastructure
    cpu_cores: int = 0
    cpu_ram: int = 0  # MB
    disk_space: float = 0.0  # GB
    inet_down: float = 0.0  # MB/s
    inet_up: float = 0.0  # MB/s

    # Status
    rentable: bool = True
    rented: bool = False
    verified: bool = False
    reliability: float = 0.0  # 0-1 score

    # Location
    geolocation: Optional[str] = None  # Country code

    # Metadata
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def hourly_rate(self) -> float:
        """Get the effective hourly rate"""
        return self.discounted_dph_total or self.dph_total

    @property
    def vram_per_gpu(self) -> int:
        """VRAM in MB per GPU"""
        return self.gpu_ram

    @property
    def is_available(self) -> bool:
        """Check if offer is currently available"""
        return self.rentable and not self.rented

    def __str__(self) -> str:
        return f"{self.num_gpus}x {self.gpu_name} @ ${self.hourly_rate:.3f}/hr"


@dataclass
class GPUInstance:
    """Represents a rented GPU instance"""

    instance_id: int
    machine_id: int
    status: str  # running, stopped, exited

    # Specs
    gpu_name: str
    num_gpus: int
    actual_status: str

    # Pricing
    dph_total: float
    total_paid: float = 0.0

    # Timing
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Access
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None

    # Metadata
    raw_data: Dict[str, Any] = field(default_factory=dict)


class VastAIClient:
    """
    Production Vast.ai API client.

    Handles authentication, rate limiting, and error handling for Vast.ai API.
    """

    BASE_URL = "https://console.vast.ai/api/v0"

    def __init__(self, api_key: str):
        """
        Initialize Vast.ai client.

        Args:
            api_key: Vast.ai API key (get from https://console.vast.ai/account/)
        """
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_delay = 0.5  # seconds between requests

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def connect(self):
        """Initialize HTTP session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            logger.info("Vast.ai client connected")

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Vast.ai client disconnected")

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API request with rate limiting.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            json_data: JSON body for POST/PUT
            params: Query parameters

        Returns:
            Response JSON

        Raises:
            aiohttp.ClientError: On API errors
        """
        if not self.session:
            await self.connect()

        url = f"{self.BASE_URL}{endpoint}"

        # Rate limiting
        await asyncio.sleep(self._rate_limit_delay)

        try:
            async with self.session.request(
                method,
                url,
                json=json_data,
                params=params
            ) as response:
                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"Vast.ai API error: {e}")
            raise

    # ==================== Search Offers ====================

    async def search_offers(
        self,
        gpu_name: Optional[str] = None,
        num_gpus: Optional[int] = None,
        min_gpu_ram: Optional[int] = None,  # MB
        max_dph: Optional[float] = None,  # Max $/hour
        min_reliability: Optional[float] = None,
        verified_only: bool = False,
        available_only: bool = True,
        limit: int = 100,
        order: Optional[List[List[str]]] = None
    ) -> List[GPUOffer]:
        """
        Search for available GPU rental offers.

        Args:
            gpu_name: Filter by GPU model (e.g., "RTX_4090", "A100")
            num_gpus: Number of GPUs required
            min_gpu_ram: Minimum GPU RAM in MB
            max_dph: Maximum price in $/hour
            min_reliability: Minimum reliability score (0-1)
            verified_only: Only show verified machines
            available_only: Only show available (non-rented) machines
            limit: Maximum offers to return
            order: Sort order [[field, direction], ...]

        Returns:
            List of GPUOffer objects
        """
        # Build filter query
        query = {
            "rentable": {
                "eq": True
            }
        }

        if available_only:
            query["rented"] = {"eq": False}

        if verified_only:
            query["verified"] = {"eq": True}

        if gpu_name:
            query["gpu_name"] = {"eq": gpu_name}

        if num_gpus:
            query["num_gpus"] = {"eq": num_gpus}

        if min_gpu_ram:
            query["gpu_ram"] = {"gte": min_gpu_ram}

        if max_dph:
            query["dph_total"] = {"lte": max_dph}

        if min_reliability:
            query["reliability"] = {"gte": min_reliability}

        # Default sort: best performance per dollar first
        if order is None:
            order = [["dlperf_per_dphtotal", "desc"]]

        payload = {
            "q": query,
            "limit": limit,
            "order": order,
            "type": "on-demand"  # or "bid" for interruptible
        }

        result = await self._request("POST", "/bundles/", json_data=payload)

        # Parse offers
        offers = []
        for offer_data in result.get("offers", []):
            offers.append(self._parse_offer(offer_data))

        logger.info(f"Found {len(offers)} GPU offers")
        return offers

    def _parse_offer(self, data: Dict[str, Any]) -> GPUOffer:
        """Parse raw offer data into GPUOffer object"""
        return GPUOffer(
            offer_id=data["id"],
            machine_id=data["machine_id"],
            host_id=data.get("host_id", 0),
            gpu_name=data["gpu_name"],
            num_gpus=data["num_gpus"],
            gpu_ram=data["gpu_ram"],
            gpu_total_ram=data["gpu_total_ram"],
            gpu_arch=data.get("gpu_arch", "nvidia"),
            dph_base=data["dph_base"],
            dph_total=data["dph_total"],
            discounted_dph_total=data.get("discounted_dph_total"),
            dlperf=data.get("dlperf"),
            dlperf_per_dphtotal=data.get("dlperf_per_dphtotal"),
            compute_cap=data.get("compute_cap"),
            cpu_cores=data.get("cpu_cores", 0),
            cpu_ram=data.get("cpu_ram", 0),
            disk_space=data.get("disk_space", 0.0),
            inet_down=data.get("inet_down", 0.0),
            inet_up=data.get("inet_up", 0.0),
            rentable=data.get("rentable", True),
            rented=data.get("rented", False),
            verified=data.get("verification", "unverified") == "verified",
            reliability=data.get("reliability2", 0.0),
            geolocation=data.get("geolocation"),
            raw_data=data
        )

    # ==================== Instance Management ====================

    async def create_instance(
        self,
        offer_id: int,
        image: str = "pytorch/pytorch:latest",
        disk_space: float = 10.0,  # GB
        label: Optional[str] = None
    ) -> GPUInstance:
        """
        Rent a GPU instance from an offer.

        Args:
            offer_id: ID of the offer to accept
            image: Docker image to run
            disk_space: Disk space in GB
            label: Optional label for instance

        Returns:
            GPUInstance object
        """
        payload = {
            "client_id": "me",
            "image": image,
            "disk": disk_space,
        }

        if label:
            payload["label"] = label

        result = await self._request(
            "PUT",
            f"/asks/{offer_id}/",
            json_data=payload
        )

        instance_data = result.get("new_contract", {})
        return self._parse_instance(instance_data)

    async def list_instances(self) -> List[GPUInstance]:
        """
        List all your active instances.

        Returns:
            List of GPUInstance objects
        """
        result = await self._request("GET", "/instances/")

        instances = []
        for instance_data in result.get("instances", []):
            instances.append(self._parse_instance(instance_data))

        return instances

    async def get_instance(self, instance_id: int) -> GPUInstance:
        """
        Get details of a specific instance.

        Args:
            instance_id: Instance ID

        Returns:
            GPUInstance object
        """
        result = await self._request("GET", f"/instances/{instance_id}")
        return self._parse_instance(result.get("instance", {}))

    async def destroy_instance(self, instance_id: int) -> bool:
        """
        Stop and destroy an instance.

        Args:
            instance_id: Instance ID to destroy

        Returns:
            True if successful
        """
        try:
            await self._request("DELETE", f"/instances/{instance_id}/")
            logger.info(f"Destroyed instance {instance_id}")
            return True
        except aiohttp.ClientError as e:
            logger.error(f"Failed to destroy instance {instance_id}: {e}")
            return False

    async def change_bid(self, instance_id: int, new_price: float) -> bool:
        """
        Change the bid price for an interruptible instance.

        Args:
            instance_id: Instance ID
            new_price: New price in $/hour

        Returns:
            True if successful
        """
        try:
            await self._request(
                "PUT",
                f"/instances/{instance_id}/",
                json_data={"price": new_price}
            )
            logger.info(f"Changed bid for instance {instance_id} to ${new_price}/hr")
            return True
        except aiohttp.ClientError as e:
            logger.error(f"Failed to change bid: {e}")
            return False

    def _parse_instance(self, data: Dict[str, Any]) -> GPUInstance:
        """Parse raw instance data into GPUInstance object"""
        return GPUInstance(
            instance_id=data["id"],
            machine_id=data["machine_id"],
            status=data.get("status_msg", "unknown"),
            gpu_name=data.get("gpu_name", "unknown"),
            num_gpus=data.get("num_gpus", 0),
            actual_status=data.get("actual_status", "unknown"),
            dph_total=data.get("dph_total", 0.0),
            total_paid=data.get("total_paid", 0.0),
            ssh_host=data.get("ssh_host"),
            ssh_port=data.get("ssh_port"),
            raw_data=data
        )

    # ==================== Market Data ====================

    async def get_market_prices(
        self,
        gpu_name: str,
        limit: int = 20
    ) -> Dict[str, float]:
        """
        Get current market pricing statistics for a GPU model.

        Args:
            gpu_name: GPU model name (e.g., "RTX_4090")
            limit: Number of offers to sample

        Returns:
            Dictionary with price statistics
        """
        offers = await self.search_offers(
            gpu_name=gpu_name,
            available_only=True,
            verified_only=True,
            limit=limit,
            order=[["dph_total", "asc"]]
        )

        if not offers:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
                "count": 0
            }

        prices = [offer.hourly_rate for offer in offers]
        prices_sorted = sorted(prices)

        return {
            "min": prices_sorted[0],
            "max": prices_sorted[-1],
            "mean": sum(prices) / len(prices),
            "median": prices_sorted[len(prices) // 2],
            "count": len(offers),
            "p25": prices_sorted[len(prices) // 4],
            "p75": prices_sorted[3 * len(prices) // 4]
        }


# Import here to avoid circular dependency
from ..core.adapters.compute import ComputeMarketplaceAdapter
from ..core.asset import ComputeAsset, AssetValuation, AssetState, AssetPosition, AssetMetadata
from ..core.venue import ActionRequest, ActionResult, ActionType


class VastAIMarketplace(ComputeMarketplaceAdapter):
    """
    Production Vast.ai marketplace adapter.

    Implements the generic Venue interface for Vast.ai GPU marketplace.
    """

    def __init__(self, api_key: str, owned_gpus: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize Vast.ai marketplace adapter.

        Args:
            api_key: Vast.ai API key
            owned_gpus: List of GPU configurations you own (for listing)
        """
        self.client = VastAIClient(api_key)
        self._initialized = False

        # Initialize parent ComputeMarketplaceAdapter
        super().__init__(
            marketplace_name="Vast.ai",
            api_key=api_key,
            owned_gpus=owned_gpus or []
        )

    async def connect(self) -> bool:
        """Connect to Vast.ai API"""
        try:
            await self.client.connect()
            self._connected = True
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Vast.ai: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Vast.ai"""
        await self.client.close()
        self._connected = False
        return True

    async def get_market_rate(self, gpu_model: str) -> float:
        """
        Get current market rate for a GPU model.

        Args:
            gpu_model: GPU model name (e.g., "RTX_4090")

        Returns:
            Current median market rate in $/hour
        """
        stats = await self.client.get_market_prices(gpu_model)
        return stats["median"]

    async def find_best_offer(
        self,
        gpu_model: str,
        max_price: Optional[float] = None
    ) -> Optional[GPUOffer]:
        """
        Find the best GPU offer for a given model.

        Args:
            gpu_model: GPU model to search for
            max_price: Maximum acceptable price

        Returns:
            Best GPUOffer or None
        """
        offers = await self.client.search_offers(
            gpu_name=gpu_model,
            max_dph=max_price,
            verified_only=True,
            limit=10,
            order=[["dlperf_per_dphtotal", "desc"]]
        )

        return offers[0] if offers else None
