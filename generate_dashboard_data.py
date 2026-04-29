#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parent
WORKBOOK = ROOT.parent / "Sentiment Analysis Masterfile-2.xlsx"
OUTPUT = ROOT / "data.js"

NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

SHEET_CONFIG = {
    "Google Reviews": {"channel": "Google Reviews", "platform": "Google Review", "brand": "COFIDIS"},
    "Trustpilot reviews": {"channel": "Trustpilot", "platform": "Trustpilot", "brand": "COFIDIS"},
    "Instagram Reel Comments": {"channel": "Instagram Reels", "platform": "Instagram Reels", "brand": "COFIDIS"},
    "FINDOMESTIC TRUSTPILOT": {"channel": "Trustpilot", "platform": "Trustpilot", "brand": "FINDOMESTIC"},
    "SELLA PERSONAL CREDIT TRUSTPILO": {
        "channel": "Trustpilot",
        "platform": "Trustpilot",
        "brand": "SELLA PERSONAL CREDIT",
    },
    "SCALAPAY TRUSTPILOT": {"channel": "Trustpilot", "platform": "Trustpilot", "brand": "SCALAPAY"},
}

THEMES = {
    "Velocità e semplicità": [
        r"rapid",
        r"veloc",
        r"immediat",
        r"semplic",
        r"facil",
        r"tempo reale",
        r"on line",
        r"online",
        r"intuitiv",
        r"comodo",
        r"pratic",
    ],
    "Assistenza clienti": [
        r"assistenza",
        r"servizio clienti",
        r"operatore",
        r"risponde",
        r"contatt",
        r"support",
        r"call center",
        r"gentil",
        r"disponib",
    ],
    "Pagamenti e rimborsi": [
        r"pagament",
        r"rata",
        r"rate",
        r"rimbor",
        r"addebit",
        r"credito",
        r"bonific",
        r"incasso",
        r"chiusura",
        r"estinzione",
        r"pratica",
    ],
    "Prezzi e trasparenza": [
        r"tasso",
        r"commission",
        r"costo",
        r"prezzo",
        r"trasparen",
        r"secci",
        r"interess",
        r"promo",
        r"promozion",
        r"pubblicità",
    ],
    "Fiducia e affidabilità": [
        r"affidab",
        r"fiduc",
        r"serio",
        r"profession",
        r"garanzia",
        r"tranquill",
        r"prevedib",
        r"sicuro",
    ],
    "Accesso e account": [
        r"access",
        r"codice",
        r"area",
        r"\bapp\b",
        r"sito",
        r"login",
        r"registraz",
        r"pagina personale",
        r"verifica",
        r"whatsapp",
    ],
    "Empatia e pressione sociale": [
        r"stipend",
        r"inflaz",
        r"rispar",
        r"scuol",
        r"famigli",
        r"spese",
        r"caff[eè]",
        r"americano",
        r"americanizzazione",
        r"soldi",
        r"crisi",
        r"euro",
        r"figli",
        r"bollette",
        r"stress",
        r"portafoglio",
    ],
}

STOPWORDS = {
    "anche",
    "ancora",
    "avere",
    "bene",
    "buona",
    "buono",
    "cose",
    "cosa",
    "dalla",
    "dalle",
    "degli",
    "della",
    "delle",
    "dello",
    "dire",
    "dopo",
    "essere",
    "fatto",
    "fare",
    "giorno",
    "giorni",
    "grazie",
    "hanno",
    "molto",
    "negli",
    "nelle",
    "negativo",
    "oppure",
    "perche",
    "perché",
    "poco",
    "positivo",
    "proprio",
    "qualche",
    "quindi",
    "quello",
    "questa",
    "questo",
    "recensione",
    "servizi",
    "servizio",
    "sempre",
    "solo",
    "sotto",
    "stato",
    "stata",
    "tutto",
    "tutti",
    "tutte",
}

QUOTES_BY_SCOPE = {
    "cofidis-all": {
        "Positive": [
            "Ho utilizzato Cofidis per un acquisto su Amazon e l’esperienza è stata davvero ottima. La procedura di richiesta è semplice e veloce, tutto chiaro e senza sorprese. Approvazione rapida e rate comode da gestire.",
        ],
        "Negative": [
            "Veloci nel prestito, ma non si riesce a parlare con un operatore.",
            "È praticamente impossibile parlare con un operatore…",
        ],
        "Neutral": [
            "Io seguo una dieta e pianifico la spesa, ho la mia dieta e so cosa prendere.",
        ],
    },
    "cofidis-trustpilot": {
        "Positive": [
            "Comodo e veloce il pagamento in 3 rate a tasso 0.",
            "Semplice, veloce, affidabile e soprattutto utile",
        ],
        "Negative": [
            "Pessimo servizio clienti. E' impossibile loggarsi nella propria pagina personale ed al servizio clienti non risponde nessuno.",
            "Solo quando ci sono promozioni a tasso zero, altrimenti meglio chiedere soldi agli strozzini.",
        ],
        "Neutral": [
            "Cofidis è una società finanziaria francese che opera in Italia da oltre 20 anni, offrendo soluzioni di credito semplici e innovative.",
        ],
    },
    "cofidis-google-reviews": {
        "Positive": [
            "Ho chiesto un prestito da ripagare a rate dal Veterinario per un’operazione costata 1300 euro. Me l’hanno accettato subito…",
        ],
        "Negative": [
            "Non è possibile parlare con un operatore…",
            "Buongiorno, ho necessità di parlare con un vostro Operatore…",
        ],
        "Neutral": [
            "Contattato da vs operatore, ricevuta proposta ampliamento linea di credito, accettata e concordato bonifico di 400 euro…",
        ],
    },
    "cofidis-instagram-reels": {
        "Positive": [
            "Lista della spesa, vado solo nelle corsie che mi interessano e vado a stomaco pieno.",
        ],
        "Negative": [
            "E c’è a chi tocca scegliere se farli o no i figli… Con questi stipendi INDECENTI, INDECOROSI.",
            "La prima strategia è non avere soldi!",
        ],
        "Neutral": [
            "Sì, il caffè ogni giorno al bar o fare colazione al bar.",
        ],
    },
}

STORY = {
    "overview": {
        "headline": "Cofidis vince sulla convenienza, ma la fiducia cala quando i clienti hanno bisogno di supporto umano.",
        "summary": "Trustpilot conferma che il prodotto funziona, Google Reviews rende visibili i punti di attrito operativi e Instagram mostra la pressione emotiva che circonda i temi legati al denaro.",
        "actions": [
            "Trasformare Google Reviews in un canale di recupero della fiducia, con risposte umane rapide e visibili su pagamenti, chiusura pratiche e problemi di accesso.",
            "Usare le prove sociali di Trustpilot in acquisizione, CRM e comunicazione ai partner commerciali per rafforzare velocità, semplicità e utilità del tasso zero.",
            "Riposizionare i contenuti Instagram su empatia e realismo, così i messaggi sul denaro riconoscono la pressione vissuta dalle persone invece di sembrare distaccati.",
        ],
    },
    "cofidis-trustpilot": {
        "headline": "Trustpilot è il motore più forte di advocacy per Cofidis.",
        "summary": "I clienti premiano con continuità velocità, semplicità e utilità concreta del pagamento rateale. Qui l'obiettivo è difendere questo vantaggio e trasformarlo in prova credibile per il marketing.",
        "actions": [
            "Valorizzare le recensioni Trustpilot più forti all'interno di creatività a pagamento e canali proprietari.",
            "Proteggere la promessa di approvazione rapida e tasso zero con indicazioni più chiare dopo l'acquisto.",
            "Invitare i clienti soddisfatti a raccontare i casi d'uso concreti in cui Cofidis ha risolto un bisogno reale.",
        ],
    },
    "cofidis-google-reviews": {
        "headline": "Google Reviews è il punto di massima pressione reputazionale.",
        "summary": "La promessa di prodotto non è il problema principale. La rottura avviene quando i clienti hanno bisogno di escalation, chiusura, rimborso o di una persona reale che risolva l'attrito.",
        "actions": [
            "Attivare un protocollo di risposta dedicato per reperibilità degli operatori, avanzamento dei rimborsi e anomalie di pagamento.",
            "Pubblicare contenuti di supporto semplici per chiusura pratica, accesso all'account, gestione del debito e rimborsi.",
            "Monitorare separatamente i casi irrisolti così Google non diventa il registro pubblico dei problemi operativi.",
        ],
    },
    "cofidis-instagram-reels": {
        "headline": "Nei commenti Instagram emerge più ansia economica che giudizio sul servizio.",
        "summary": "Il tono negativo è guidato soprattutto dal contesto sociale: stipendi, costi scolastici, inflazione e pressione domestica. In questo scenario la sola comunicazione promozionale fatica a funzionare.",
        "actions": [
            "Costruire contenuti centrati su empatia, praticità e momenti realistici di gestione del budget.",
            "Moderare con un tono di assistenza social che riconosca la pressione economica invece di riportare troppo in fretta il discorso sul prodotto.",
            "Usare volti, testimonianze e testi che presentino Cofidis come uno strumento utile, non come un marchio finanziario astratto.",
        ],
    },
    "benchmark": {
        "headline": "Cofidis è competitiva sulla velocità, ma i concorrenti trasmettono più sicurezza e completezza dopo l'approvazione.",
        "summary": "Sella vince sulla qualità percepita del supporto umano, Scalapay alza l'asticella sulle rate senza attrito e Findomestic mostra come il tono dell'assistenza possa limitare il danno reputazionale.",
        "actions": [
            "Chiudere prima di tutto il divario sull'assistenza: è lì che i concorrenti risultano più affidabili e rassicuranti.",
            "Trasformare la velocità in rassicurazione spiegando bene cosa succede dopo l'approvazione, non solo prima.",
            "Rivedere la comunicazione su prezzi e chiusura pratiche, così l'attrito non si trasforma in un problema di equità percepita.",
        ],
    },
}

MANAGEMENT_TABLE = [
    {
        "theme": "Assistenza clienti irraggiungibile",
        "implication": "Quando i canali di contatto falliscono, anche i problemi piccoli si trasformano in rotture pubbliche di fiducia.",
    },
    {
        "theme": "Anomalie di pagamento e addebito",
        "implication": "L'attrito operativo viene letto come inaffidabilità quando il marchio aumenta la pressione più velocemente di quanto chiarisca.",
    },
    {
        "theme": "Rimborsi, chiusura ed escalation sul debito",
        "implication": "I clienti giudicano il marchio con maggiore severità nella gestione delle eccezioni, non durante l'approvazione.",
    },
    {
        "theme": "Tassi, costi e trasparenza",
        "implication": "Qualsiasi mancanza di chiarezza sul prezzo trasforma facilmente un'esperienza neutra in una negativa.",
    },
    {
        "theme": "Frustrazione economica su Instagram",
        "implication": "Il pubblico sta discutendo di accessibilità economica ed equità, quindi l'empatia conta più della promozione.",
    },
]

BENCHMARK_NOTES = [
    "Scalapay fissa il livello più alto della categoria sulle rate senza attrito, con il 97,0% di recensioni positive.",
    "Sella Personal Credit supera Cofidis sia per quota positiva sia per contenimento del negativo, aiutata da segnali più forti di assistenza umana.",
    "Findomestic mostra una quota positiva più bassa, ma raccoglie comunque meno recensioni apertamente negative rispetto a Cofidis.",
]


@dataclass
class Review:
    id: str
    sheet: str
    brand: str
    channel: str
    platform: str
    name: str
    review: str
    date: str
    vote: float | None
    sentiment: str
    themes: list[str]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def column_to_number(column: str) -> int:
    number = 0
    for char in column:
        if "A" <= char <= "Z":
            number = number * 26 + ord(char) - 64
    return number


def parse_shared_strings(archive: ZipFile) -> list[str]:
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings = []
    for node in root.findall("main:si", NS):
        strings.append("".join(text.text or "" for text in node.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))
    return strings


def workbook_targets(archive: ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {node.attrib["Id"]: "xl/" + node.attrib["Target"] for node in rels}
    return {
        sheet.attrib["name"]: rel_map[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
        for sheet in workbook.find("main:sheets", NS)
    }


def read_rows(archive: ZipFile, target: str, shared_strings: list[str], max_columns: int = 5) -> list[list[str]]:
    root = ET.fromstring(archive.read(target))
    rows = []
    for row in root.findall(".//main:sheetData/main:row", NS):
        values = [""] * max_columns
        touched = False
        for cell in row.findall("main:c", NS):
            match = re.match(r"([A-Z]+)(\d+)", cell.attrib["r"])
            column = column_to_number(match.group(1))
            if not 1 <= column <= max_columns:
                continue
            cell_type = cell.attrib.get("t")
            value = ""
            node = cell.find("main:v", NS)
            inline = cell.find("main:is", NS)
            if cell_type == "s" and node is not None:
                value = shared_strings[int(node.text)]
            elif cell_type == "inlineStr" and inline is not None:
                value = "".join(text.text or "" for text in inline.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
            elif node is not None:
                value = node.text
            values[column - 1] = value
            touched = True
        if touched and any(item != "" for item in values):
            rows.append(values)
    return rows


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_date(value: str) -> str:
    value = normalize_whitespace(value)
    if re.fullmatch(r"\d+(\.0+)?", value):
        days = int(float(value))
        if 35000 < days < 50000:
            return (datetime(1899, 12, 30) + timedelta(days=days)).date().isoformat()
    return value


def detect_themes(text: str) -> list[str]:
    lowered = text.lower()
    return [theme for theme, patterns in THEMES.items() if any(re.search(pattern, lowered) for pattern in patterns)]


def top_keywords(rows: list[Review], sentiment: str, limit: int = 8) -> list[str]:
    tokens = Counter()
    for row in rows:
        if row.sentiment != sentiment:
            continue
        for token in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", row.review.lower()):
            if len(token) < 4 or token in STOPWORDS:
                continue
            tokens[token] += 1
    return [token for token, _ in tokens.most_common(limit)]


def theme_counts(rows: list[Review]) -> dict[str, dict[str, int]]:
    output = {theme: {"Positive": 0, "Neutral": 0, "Negative": 0} for theme in THEMES}
    for row in rows:
        for theme in row.themes:
            output[theme][row.sentiment] += 1
    return output


def summarize(rows: list[Review], scope_id: str, label: str, scope_type: str) -> dict:
    counts = Counter(row.sentiment for row in rows)
    total = len(rows)
    positive = counts["Positive"]
    neutral = counts["Neutral"]
    negative = counts["Negative"]
    rates = {
        "positive": round(positive / total * 100, 1) if total else 0.0,
        "neutral": round(neutral / total * 100, 1) if total else 0.0,
        "negative": round(negative / total * 100, 1) if total else 0.0,
    }
    mentions = theme_counts(rows)
    positive_themes = sorted(
        [{"theme": theme, "count": values["Positive"]} for theme, values in mentions.items() if values["Positive"]],
        key=lambda item: (-item["count"], item["theme"]),
    )
    negative_themes = sorted(
        [{"theme": theme, "count": values["Negative"]} for theme, values in mentions.items() if values["Negative"]],
        key=lambda item: (-item["count"], item["theme"]),
    )
    neutral_themes = sorted(
        [{"theme": theme, "count": values["Neutral"]} for theme, values in mentions.items() if values["Neutral"]],
        key=lambda item: (-item["count"], item["theme"]),
    )
    quotes = QUOTES_BY_SCOPE.get(scope_id, {})
    return {
        "id": scope_id,
        "label": label,
        "scopeType": scope_type,
        "totalComments": total,
        "counts": {"positive": positive, "neutral": neutral, "negative": negative},
        "rates": rates,
        "netSentiment": round(rates["positive"] - rates["negative"], 1),
        "themeMentions": mentions,
        "topPositiveThemes": positive_themes[:4],
        "topNegativeThemes": negative_themes[:4],
        "topNeutralThemes": neutral_themes[:4],
        "topKeywords": {
            "positive": top_keywords(rows, "Positive"),
            "neutral": top_keywords(rows, "Neutral"),
            "negative": top_keywords(rows, "Negative"),
        },
        "quotes": quotes,
    }


def review_to_dict(review: Review) -> dict:
    return {
        "id": review.id,
        "sheet": review.sheet,
        "brand": review.brand,
        "channel": review.channel,
        "platform": review.platform,
        "name": review.name,
        "review": review.review,
        "date": review.date,
        "vote": review.vote,
        "sentiment": review.sentiment,
        "themes": review.themes,
    }


def main() -> None:
    with ZipFile(WORKBOOK) as archive:
        shared_strings = parse_shared_strings(archive)
        targets = workbook_targets(archive)
        reviews: list[Review] = []
        for sheet_name, meta in SHEET_CONFIG.items():
            rows = read_rows(archive, targets[sheet_name], shared_strings, max_columns=5)
            for index, (name, review, date, vote, sentiment) in enumerate(rows[1:], start=1):
                cleaned_review = normalize_whitespace(review)
                reviews.append(
                    Review(
                        id=f"{slugify(meta['brand'])}-{slugify(meta['channel'])}-{index}",
                        sheet=sheet_name,
                        brand=meta["brand"],
                        channel=meta["channel"],
                        platform=meta["platform"],
                        name=normalize_whitespace(name) or "Anonimo",
                        review=cleaned_review,
                        date=parse_date(date),
                        vote=float(vote) if vote else None,
                        sentiment=sentiment,
                        themes=detect_themes(cleaned_review),
                    )
                )

    cof_reviews = [review for review in reviews if review.brand == "COFIDIS"]
    trustpilot_reviews = [review for review in reviews if review.channel == "Trustpilot"]

    scope_rows = {
        "cofidis-all": cof_reviews,
        "cofidis-trustpilot": [review for review in cof_reviews if review.channel == "Trustpilot"],
        "cofidis-google-reviews": [review for review in cof_reviews if review.channel == "Google Reviews"],
        "cofidis-instagram-reels": [review for review in cof_reviews if review.channel == "Instagram Reels"],
        "findomestic-trustpilot": [review for review in trustpilot_reviews if review.brand == "FINDOMESTIC"],
        "sella-personal-credit-trustpilot": [
            review for review in trustpilot_reviews if review.brand == "SELLA PERSONAL CREDIT"
        ],
        "scalapay-trustpilot": [review for review in trustpilot_reviews if review.brand == "SCALAPAY"],
    }

    scopes = {
        "cofidis-all": summarize(scope_rows["cofidis-all"], "cofidis-all", "Tutti i canali Cofidis", "brand"),
        "cofidis-trustpilot": summarize(
            scope_rows["cofidis-trustpilot"], "cofidis-trustpilot", "Cofidis su Trustpilot", "channel"
        ),
        "cofidis-google-reviews": summarize(
            scope_rows["cofidis-google-reviews"], "cofidis-google-reviews", "Cofidis su Google Reviews", "channel"
        ),
        "cofidis-instagram-reels": summarize(
            scope_rows["cofidis-instagram-reels"], "cofidis-instagram-reels", "Cofidis su Instagram Reels", "channel"
        ),
        "findomestic-trustpilot": summarize(
            scope_rows["findomestic-trustpilot"], "findomestic-trustpilot", "Findomestic su Trustpilot", "benchmark"
        ),
        "sella-personal-credit-trustpilot": summarize(
            scope_rows["sella-personal-credit-trustpilot"],
            "sella-personal-credit-trustpilot",
            "Sella Personal Credit su Trustpilot",
            "benchmark",
        ),
        "scalapay-trustpilot": summarize(
            scope_rows["scalapay-trustpilot"], "scalapay-trustpilot", "Scalapay su Trustpilot", "benchmark"
        ),
    }

    cof_total = scopes["cofidis-all"]["totalComments"] or 1
    for scope_id in ("cofidis-trustpilot", "cofidis-google-reviews", "cofidis-instagram-reels"):
        scope = scopes[scope_id]
        volume_share = round(scope["totalComments"] / cof_total * 100, 1)
        scope["volumeShare"] = volume_share
        scope["priorityScore"] = round(scope["rates"]["negative"] * 0.65 + volume_share * 0.35, 1)

    trust_total = sum(scopes[key]["totalComments"] for key in ("cofidis-trustpilot", "findomestic-trustpilot", "sella-personal-credit-trustpilot", "scalapay-trustpilot")) or 1
    for scope_id in (
        "cofidis-trustpilot",
        "findomestic-trustpilot",
        "sella-personal-credit-trustpilot",
        "scalapay-trustpilot",
    ):
        scope = scopes[scope_id]
        scope["trustpilotVolumeShare"] = round(scope["totalComments"] / trust_total * 100, 1)

    benchmark_rows = [
        {
            "brand": "COFIDIS",
            "scopeId": "cofidis-trustpilot",
            **scopes["cofidis-trustpilot"],
        },
        {
            "brand": "FINDOMESTIC",
            "scopeId": "findomestic-trustpilot",
            **scopes["findomestic-trustpilot"],
        },
        {
            "brand": "SELLA PERSONAL CREDIT",
            "scopeId": "sella-personal-credit-trustpilot",
            **scopes["sella-personal-credit-trustpilot"],
        },
        {
            "brand": "SCALAPAY",
            "scopeId": "scalapay-trustpilot",
            **scopes["scalapay-trustpilot"],
        },
    ]

    top_overall_negative_theme = scopes["cofidis-all"]["topNegativeThemes"][0]["theme"]
    strongest_positive_theme = scopes["cofidis-all"]["topPositiveThemes"][0]["theme"]

    data = {
        "meta": {
            "title": "Dashboard del sentiment Cofidis",
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "sources": [
                "Sentiment Analysis Masterfile-2.xlsx",
                "Cofidis Sentiment Analysis Conclusione.docx",
            ],
        },
        "story": STORY,
        "managementTable": MANAGEMENT_TABLE,
        "benchmarkNotes": BENCHMARK_NOTES,
        "scopeOrder": [
            "cofidis-all",
            "cofidis-trustpilot",
            "cofidis-google-reviews",
            "cofidis-instagram-reels",
        ],
        "scopes": scopes,
        "channelComparison": [
            {"scopeId": "cofidis-trustpilot", "channel": "Trustpilot", **scopes["cofidis-trustpilot"]},
            {"scopeId": "cofidis-google-reviews", "channel": "Google Reviews", **scopes["cofidis-google-reviews"]},
            {"scopeId": "cofidis-instagram-reels", "channel": "Instagram Reels", **scopes["cofidis-instagram-reels"]},
        ],
        "benchmarkComparison": benchmark_rows,
        "highlights": {
            "overallPositiveRate": scopes["cofidis-all"]["rates"]["positive"],
            "overallNegativeRate": scopes["cofidis-all"]["rates"]["negative"],
            "overallNetSentiment": scopes["cofidis-all"]["netSentiment"],
            "highestRiskChannel": max(
                (
                    scopes["cofidis-trustpilot"],
                    scopes["cofidis-google-reviews"],
                    scopes["cofidis-instagram-reels"],
                ),
                key=lambda item: item["priorityScore"],
            )["label"],
            "topPainPoint": top_overall_negative_theme,
            "topAdvocacyDriver": strongest_positive_theme,
        },
        "themes": list(THEMES.keys()),
        "reviews": [review_to_dict(review) for review in reviews],
    }

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    OUTPUT.write_text(f"window.DASHBOARD_DATA = {payload};\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
