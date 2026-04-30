"""VGP - cluster pipeline vettoriale (ADR-0018).

Inaugurato in CHG-2026-04-30-027 con `is_vetoed_by_roi` - predicato
scalare R-08 (Veto ROI Minimo).

Esteso in CHG-2026-04-30-034 con `min_max_normalize` - primitiva
vettoriale L04b (normalizzazione min-max [0,1] sul listino di sessione,
escludendo righe KILLED dal calcolo di min/max).

Completato lo scoring in CHG-2026-04-30-035 con `compute_vgp_score` -
formula VGP composita verbatim PROJECT-RAW.md (pesi 0.4/0.4/0.2) +
applicazione vettoriale di R-05 KILL-SWITCH e R-08 VETO ROI.

La pipeline orchestratrice end-to-end (`compute_vgp_session` di
ADR-0018, partendo dal listino raw con calcolo F1/F2/F4/F5 incluso)
e' scope di un CHG successivo.
"""

from talos.vgp.normalize import min_max_normalize
from talos.vgp.score import (
    CASH_PROFIT_WEIGHT,
    ROI_WEIGHT,
    VELOCITY_WEIGHT,
    compute_vgp_score,
)
from talos.vgp.veto import DEFAULT_ROI_VETO_THRESHOLD, is_vetoed_by_roi

__all__ = [
    "CASH_PROFIT_WEIGHT",
    "DEFAULT_ROI_VETO_THRESHOLD",
    "ROI_WEIGHT",
    "VELOCITY_WEIGHT",
    "compute_vgp_score",
    "is_vetoed_by_roi",
    "min_max_normalize",
]
