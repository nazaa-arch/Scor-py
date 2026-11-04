"""SCOR-Py: Toolkit Metrik & Simulasi Rantai Pasok Berbasis Kerangka SCOR.

Implements SCOR (Supply Chain Operations Reference) metrics:
- Reliability (RL.1.1, OTIF, On-Time, In-Full, Damage-Free, Doc-Accurate)
- Responsiveness (RS.1.1 Order Fulfillment Cycle Time)
- Asset Management Efficiency (AM.1.1 Cash-to-Cash, AM.1.2 ROFA, AM.1.3 ROWC)
- Cost (CO.1.1 Total Supply Chain Management Cost)
- Agility & What-If Monte Carlo Simulation (AG.1.1, SupplyChainSimulator)
"""

from scorpy.asset_efficiency import AssetMetrics
from scorpy.cost import CostMetrics
from scorpy.reliability import ReliabilityMetrics
from scorpy.responsiveness import ResponsivenessMetrics
from scorpy.schema import (
    SchemaValidationError,
    validate_financials,
    validate_inventory,
    validate_orders,
)
from scorpy.simulator import SimulationResult, SupplyChainSimulator

__version__ = "0.1.0"
__all__ = [
    "ReliabilityMetrics",
    "ResponsivenessMetrics",
    "AssetMetrics",
    "CostMetrics",
    "SupplyChainSimulator",
    "SimulationResult",
    "validate_orders",
    "validate_financials",
    "validate_inventory",
    "SchemaValidationError",
    "__version__",
]
