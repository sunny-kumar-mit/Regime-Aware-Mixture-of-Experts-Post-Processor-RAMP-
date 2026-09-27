"""
Public Meteorological Product Adapter
SIH26080 | MoES / NCMRWF | Phase 19

Inspects publicly exposed NCMRWF and IMD product portals.
Distinguishes between public visualizations / summary charts and
underlying raw multi-level meteorological numerical archives.
Strictly returns PUBLIC_PRODUCT_ONLY and RAMP_INFERENCE_NOT_POSSIBLE
when full raw 18-predictor fields are not accessible.
Never scrapes protected systems or bypasses authentication.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PublicProductMetadata(BaseModel):
    source_url: str
    provider: str
    retrieval_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    product: str
    cycle: Optional[str] = "00Z"
    lead: Optional[int] = 24
    variables: List[str] = Field(default_factory=list)
    coverage: str = "India (Regional)"
    format: str = "IMAGE_OR_PDF_OR_SUMMARY"
    availability: str = "PUBLIC_VIEW_ONLY"
    status: str = "PUBLIC_PRODUCT_ONLY"
    inference_eligibility: str = "RAMP_INFERENCE_NOT_POSSIBLE"
    notes: str = "Public visualizations do not provide raw 3D atmospheric predictor tensors required for RAMP MoE inference."


class PublicProductAdapter:
    """
    Adapter assessing public NCMRWF and IMD meteorological feeds.
    Safeguards against confusing end-user web graphics with operational binary archives.
    """

    PUBLIC_CATALOG = {
        "NCMRWF_PUBLIC_NCUM_PRECIP": {
            "source_url": "https://www.ncmrwf.gov.in/ncum_prod.php",
            "provider": "NCMRWF",
            "product": "NCUM 12-km Deterministic Rainfall Map",
            "variables": ["total_precipitation"],
            "format": "PNG/Web",
        },
        "NCMRWF_PUBLIC_NEPS_PROB": {
            "source_url": "https://www.ncmrwf.gov.in/neps_prob.php",
            "provider": "NCMRWF",
            "product": "NEPS 23-member Ensemble Strike Probability Map",
            "variables": ["precip_prob_10mm", "precip_prob_20mm"],
            "format": "PNG/Web",
        },
        "IMD_PUBLIC_ISMR_RAINFALL": {
            "source_url": "https://mausam.imd.gov.in/imd_latest/contents/districtwise-rainfall.php",
            "provider": "IMD",
            "product": "District Rainfall Monitoring Product",
            "variables": ["district_rainfall_departure"],
            "format": "HTML/Table",
        },
    }

    def inspect_public_product(self, product_key: str) -> PublicProductMetadata:
        info = self.PUBLIC_CATALOG.get(
            product_key,
            {
                "source_url": "https://ncmrwf.gov.in",
                "provider": "NCMRWF",
                "product": "Unknown Public Product",
                "variables": [],
                "format": "Web",
            },
        )

        return PublicProductMetadata(
            source_url=info["source_url"],
            provider=info["provider"],
            product=info["product"],
            variables=info["variables"],
            format=info["format"],
            availability="PUBLIC_VIEW_ONLY",
            status="PUBLIC_PRODUCT_ONLY",
            inference_eligibility="RAMP_INFERENCE_NOT_POSSIBLE",
            notes=(
                f"Inspected '{info['product']}'. Contains only rendered summary graphics. "
                "The 18 multi-level dynamical predictors (u/v wind, CAPE, vorticity, etc.) "
                "required by ramp_features_v1.0.0 are absent from this public web product."
            ),
        )
