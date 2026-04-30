"""ROI - Return On Investment (interpretazione standard FBA flipping).

    ROI = Cash_Profit / Costo_Fornitore

Verbatim PROJECT-RAW.md sez. 6.3 Formula VGP, riga "ROI_Percentuale":
*"Rapporto tra utile e costo (es. 0.15 per il 15%)"*. Mappatura:
- "utile" -> `Cash_Profit` (F2, CHG-2026-04-30-026)
- "costo" -> `Costo_Fornitore` (input)

Output e' frazione decimale, non percentuale: `roi == 0.08` significa
8%. Convenzione esplicita per evitare la trappola classica "8% vs
0.08". Coerente con `referral_fee_rate` di CHG-025 (stesso dominio
[0, 1] semanticamente, anche se ROI puo' sforare in entrambe le
direzioni).

ROI e' il **gate** del Veto R-08: ASIN con `roi < soglia` (default
8% = 0.08, configurabile dal cruscotto - L10) viene scartato dal
Tetris a prescindere dal VGP score. Il veto stesso e' scope di un
CHG separato; questa funzione produce solo lo scalare.

R-01 NO SILENT DROPS:
- `costo_fornitore_eur <= 0` solleva `ValueError` (zero proibito:
  divisione-per-zero non ha significato per "rapporto utile/costo";
  negativo: spesa fisicamente impossibile).
- `cash_profit_eur` non validato per segno: puo' essere qualsiasi
  float (output di F2 che ammette negativi). ROI negativo e'
  informazione economica utile (loss-leader -> Veto R-08 lo scarta
  comunque, ma il valore va calcolato e log-gato).
"""

from __future__ import annotations


def roi(
    cash_profit_eur: float,
    costo_fornitore_eur: float,
) -> float:
    """Calcola il ROI come frazione decimale (ADR-0018).

    >>> round(roi(64.5922, 100.0), 4)
    0.6459

    :param cash_profit_eur: output di F2, in EUR. Puo' essere
        negativo (loss-leader), nessuna validazione di segno.
    :param costo_fornitore_eur: spesa di acquisto unitario in EUR.
        Deve essere strettamente > 0 (zero proibito:
        divisione-per-zero senza significato).
    :returns: ROI come frazione decimale (es. `0.08` = 8%, soglia
        Veto R-08 default). Puo' essere negativo (loss).
    :raises ValueError: se `costo_fornitore_eur <= 0`.
    """
    if costo_fornitore_eur <= 0:
        msg = (
            f"costo_fornitore_eur invalido per ROI: {costo_fornitore_eur}. "
            "Deve essere > 0 (zero proibito: divisione-per-zero)."
        )
        raise ValueError(msg)

    return cash_profit_eur / costo_fornitore_eur
