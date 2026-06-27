"""Curated abbreviation / synonym expansion map (brief §8.1).

RU/KK/Latin medical shorthand → canonical-ish full forms. Used by preprocess to
expand raw names before matching. Intentionally conservative and extensible; the
learning loop grows per-service synonyms separately in the DB.
"""
from __future__ import annotations

# Whole-token replacements (matched on word boundaries, case-insensitive, post-lowercasing).
ABBREVIATIONS: dict[str, str] = {
    # Hematology / common labs
    "оак": "общий анализ крови",
    "cbc": "общий анализ крови",
    "кл ан крови": "общий анализ крови",
    "оам": "общий анализ мочи",
    "б/х": "биохимический",
    "бх": "биохимический",
    "б х": "биохимический",
    "коаг": "коагулология",
    # Hormones / immunoassay
    "ттг": "тиреотропный гормон",
    "tsh": "тиреотропный гормон",
    "т3": "трийодтиронин",
    "т4": "тироксин",
    "ифа": "иммуноферментный анализ",
    "пцр": "полимеразная цепная реакция",
    "пса": "простатспецифический антиген",
    # Imaging / functional
    "узи": "ультразвуковое исследование",
    "обп": "органов брюшной полости",
    "огк": "органов грудной клетки",
    "омт": "органов малого таза",
    "ктг": "кардиотокография",
    "экг": "электрокардиография",
    "ээг": "электроэнцефалография",
    "кт": "компьютерная томография",
    "мрт": "магнитно-резонансная томография",
    "ро": "рентген",
    "рг": "рентгенография",
    # Specialist consults
    "консульт": "консультация",
    "первич": "первичный",
    "повтор": "повторный",
    # Kazakh fragments commonly seen
    "қан": "кровь",
    "талдау": "анализ",
}

# Noise qualifiers stripped from the matching string but kept as tie-break features.
NOISE_QUALIFIERS: list[str] = [
    "взрослый",
    "детский",
    "ребёнок",
    "ребенок",
    "1 кат",
    "2 кат",
    "3 кат",
    "категория",
    "кат",
    "первая категория",
    "высшая категория",
    "руб",
    "тенге",
    "услуга",
    "прейскурант",
]
