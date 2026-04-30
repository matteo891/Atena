"""VGP - cluster pipeline vettoriale (ADR-0018).

Inaugurato in CHG-2026-04-30-027 con `is_vetoed_by_roi` - predicato
scalare R-08 (Veto ROI Minimo). Le versioni vettoriali su DataFrame
di sessione (normalize/score/veto vettoriale) sono scope futuro.
"""

from talos.vgp.veto import DEFAULT_ROI_VETO_THRESHOLD, is_vetoed_by_roi

__all__ = ["DEFAULT_ROI_VETO_THRESHOLD", "is_vetoed_by_roi"]
