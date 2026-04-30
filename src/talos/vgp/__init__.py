"""VGP - cluster pipeline vettoriale (ADR-0018).

Inaugurato in CHG-2026-04-30-027 con `is_vetoed_by_roi` - predicato
scalare R-08 (Veto ROI Minimo).

Esteso in CHG-2026-04-30-034 con `min_max_normalize` - primitiva
vettoriale L04b (normalizzazione min-max [0,1] sul listino di sessione,
escludendo righe KILLED dal calcolo di min/max). Prima funzione del
cluster a operare su `pd.Series` (ergo primo consumatore architetturale
di pandas).

Le funzioni `vgp/score.py` (formula VGP completa) e `vgp/veto.py`
vettoriale (su DataFrame N-righe) sono scope di CHG successivi.
"""

from talos.vgp.normalize import min_max_normalize
from talos.vgp.veto import DEFAULT_ROI_VETO_THRESHOLD, is_vetoed_by_roi

__all__ = ["DEFAULT_ROI_VETO_THRESHOLD", "is_vetoed_by_roi", "min_max_normalize"]
