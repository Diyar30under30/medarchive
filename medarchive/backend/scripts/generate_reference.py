"""Generate a realistic synthetic canonical directory `Справочник услуг.xlsx`.

Mirrors the organizers' verified schema and caveats (brief §4) so the whole
pipeline is buildable/testable before the real file arrives:
  columns: ID | Специальность | Code | Name_ru | TarificatrCode
  - No column is a usable primary key (Code duplicates; TarificatrCode missing
    on some rows; ID is a specialty-group id).
  - Name_ru repeats across specialties (e.g. Колоноскопия, 3D УЗИ плода).
  - Large lab groups (ИФА, Биохимия, Коагулология, УЗИ, ПЦР) with many near-
    identical analyte names.

Run:  python -m scripts.generate_reference
Drop the REAL file into data/reference/ to override (loader is idempotent).
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from app.config import settings

# (Специальность, ID group, [Name_ru, ...]) — representative, RU + some KK.
CATALOG: list[tuple[str, int, list[str]]] = [
    ("Биохимия", 11, [
        "Глюкоза", "Холестерин общий", "Холестерин ЛПВП", "Холестерин ЛПНП",
        "Триглицериды", "Билирубин общий", "Билирубин прямой", "АЛТ", "АСТ",
        "Креатинин", "Мочевина", "Мочевая кислота", "Общий белок", "Альбумин",
        "Амилаза", "Щелочная фосфатаза", "Калий", "Натрий", "Кальций общий",
        "Железо сыворотки", "Ферритин", "С-реактивный белок",
    ]),
    ("ИФА", 12, [
        "Тиреотропный гормон (ТТГ)", "Свободный тироксин (Т4 свободный)",
        "Трийодтиронин свободный (Т3 свободный)", "Антитела к ТПО",
        "Пролактин", "Кортизол", "Тестостерон общий", "Эстрадиол",
        "Прогестерон", "ЛГ", "ФСГ", "Инсулин", "С-пептид",
        "Простатспецифический антиген общий (ПСА)", "АФП", "РЭА", "СА-125",
        "СА 19-9", "Витамин D (25-ОН)", "Витамин B12",
    ]),
    ("Коагулология", 13, [
        "Протромбиновое время", "МНО", "АЧТВ", "Фибриноген", "Д-димер",
        "Антитромбин III", "Тромбиновое время",
    ]),
    ("Гематология", 14, [
        "Общий анализ крови", "Общий анализ крови с лейкоформулой",
        "СОЭ", "Ретикулоциты", "Подсчёт тромбоцитов",
    ]),
    ("Общеклинические исследования", 15, [
        "Общий анализ мочи", "Анализ мочи по Нечипоренко",
        "Копрограмма", "Кал на скрытую кровь", "Соскоб на энтеробиоз",
    ]),
    ("ПЦР", 16, [
        "ПЦР на хламидии", "ПЦР на микоплазму", "ПЦР на уреаплазму",
        "ПЦР на ВПЧ (16/18)", "ПЦР на цитомегаловирус", "ПЦР на ВЭБ",
        "ПЦР на герпес 1/2 типа", "ПЦР на гонококк", "ПЦР на трихомонаду",
        "ПЦР на SARS-CoV-2",
    ]),
    ("УЗИ", 17, [
        "УЗИ органов брюшной полости", "УЗИ почек", "УЗИ щитовидной железы",
        "УЗИ молочных желёз", "УЗИ органов малого таза", "УЗИ предстательной железы",
        "Эхокардиография", "УЗИ сосудов шеи", "3D УЗИ плода", "Колоноскопия",
    ]),
    ("Эндоскопия", 18, [
        "Гастроскопия", "Колоноскопия", "Бронхоскопия", "Ректороманоскопия",
    ]),
    ("Функциональная диагностика", 19, [
        "Электрокардиография (ЭКГ)", "Холтеровское мониторирование ЭКГ",
        "Суточное мониторирование АД", "Электроэнцефалография (ЭЭГ)",
        "Спирография", "Кардиотокография (КТГ)",
    ]),
    ("Рентгенология", 20, [
        "Рентгенография органов грудной клетки", "Рентгенография позвоночника",
        "Маммография", "Флюорография", "Компьютерная томография головного мозга",
        "Магнитно-резонансная томография позвоночника",
    ]),
    ("Консультации специалистов", 21, [
        "Консультация терапевта", "Консультация кардиолога",
        "Консультация эндокринолога", "Консультация гинеколога",
        "Консультация уролога", "Консультация невролога",
        "Консультация офтальмолога", "Консультация дерматолога",
        "Консультация хирурга", "Консультация оториноларинголога",
    ]),
    ("Дерматология", 22, [
        "Удаление папиллом", "Удаление бородавок", "Дерматоскопия",
    ]),
    ("Хирургия", 23, [
        "Удаление папиллом", "Вскрытие абсцесса", "Перевязка раны",
        "Удаление атеромы",
    ]),
    ("Гинекология", 24, [
        "Кольпоскопия", "Удаление папиллом", "Установка ВМС",
        "Цитологическое исследование (ПАП-тест)",
    ]),
    ("Физиотерапия", 25, [
        "Электрофорез", "Магнитотерапия", "УВЧ-терапия", "Лазеротерапия",
    ]),
    ("Стоматология", 26, [
        "Консультация стоматолога", "Лечение кариеса", "Удаление зуба",
        "Профессиональная гигиена полости рта",
    ]),
    # Kazakh-language duplicates of common services (bilingual directory).
    ("Зертханалық диагностика", 27, [
        "Қанның жалпы талдауы", "Зәрдің жалпы талдауы", "Қандағы глюкоза",
    ]),
]


def _code(group: int, idx: int) -> str:
    """Codes intentionally collide across the directory (heavy duplication)."""
    return f"K{group:02d}{(idx % 7) + 1:02d}"  # only 7 distinct codes per group


def build_rows() -> list[dict]:
    rows: list[dict] = []
    running = 0
    for specialty, gid, names in CATALOG:
        for i, name in enumerate(names):
            running += 1
            # TarificatrCode missing on ~1 in 8 rows (matches the real ~82/1286).
            tarif = "" if running % 8 == 0 else f"T{gid}{i:03d}"
            rows.append(
                {
                    "ID": gid,
                    "Специальность": specialty,
                    "Code": _code(gid, i),
                    "Name_ru": name,
                    "TarificatrCode": tarif,
                }
            )
    return rows


def main() -> Path:
    rows = build_rows()
    wb = Workbook()
    ws = wb.active
    ws.title = "Справочник"
    headers = ["ID", "Специальность", "Code", "Name_ru", "TarificatrCode"]
    ws.append(headers)
    for r in rows:
        ws.append([r[h] for h in headers])

    out_dir = settings.reference_path
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "Справочник услуг.xlsx"
    wb.save(out_path)

    specialties = {r["Специальность"] for r in rows}
    print(
        f"Wrote {len(rows)} services across {len(specialties)} specialties → {out_path}"
    )
    return out_path


if __name__ == "__main__":
    main()
