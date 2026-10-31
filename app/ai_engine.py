import json
import logging
import re
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger("ai_engine")

STYLE_PROMPTS = {
    "freundlich": "Höflich, sympathisch, wertschätzend und zuvorkommend. Zeige ehrliches Interesse am Artikel.",
    "sachlich": "Präzise, sachlich, direkt auf den Punkt, ohne ausschweifende Floskeln. Klarer Fokus auf Zustand und Fakten.",
    "hartnaeckig": "Selbstbewusst, bestimmt, mit guten Gegenargumenten (Gebrauchsspuren, Alternativen, Marktwert) verhandeln, aber stets respektvoll.",
    "schnaeppchenjaeger": "Fokussiert auf schnellen Abschluss ('kann sofort bar abholen' oder 'zahle sofort per PayPal mit Käuferschutz'), zielt auf maximalen Preisnachlass ab."
}

def call_llm_api(
    provider: str,
    api_key: str,
    model: str,
    prompt: str,
    system_prompt: str = "",
    ollama_url: str = "http://localhost:11434"
) -> Optional[str]:
    """
    Universeller Aufruf für unterstützte KI-Provider:
    Gemini, DeepSeek, OpenAI, Claude, Kimi (Moonshot), Ollama.
    Gibt den Text der Antwort zurück oder None bei Fehlern.
    """
    provider = (provider or "").lower().strip()
    if not provider or provider in ("heuristic", "none", "aus"):
        return None

    try:
        if provider == "gemini":
            mod = model.strip() or "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{system_prompt}\n\n{prompt}" if system_prompt else prompt}]
                    }
                ],
                "generationConfig": {"temperature": 0.4}
            }
            res = requests.post(url, json=payload, timeout=20)
            if res.status_code == 200:
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.warning(f"Gemini API Fehler: {res.status_code} - {res.text}")

        elif provider in ("openai", "deepseek", "kimi"):
            base_url = "https://api.openai.com/v1"
            def_model = "gpt-4o-mini"
            if provider == "deepseek":
                base_url = "https://api.deepseek.com/v1"
                def_model = "deepseek-chat"
            elif provider == "kimi":
                base_url = "https://api.moonshot.cn/v1"
                def_model = "moonshot-v1-8k"

            mod = model.strip() or def_model
            url = f"{base_url}/chat/completions"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            }
            res = requests.post(url, json={"model": mod, "messages": messages, "temperature": 0.4}, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
            logger.warning(f"{provider} API Fehler: {res.status_code} - {res.text}")

        elif provider == "claude":
            mod = model.strip() or "claude-3-5-sonnet-20241022"
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key.strip(),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            payload = {
                "model": mod,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            }
            if system_prompt:
                payload["system"] = system_prompt

            res = requests.post(url, json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                return data["content"][0]["text"].strip()
            logger.warning(f"Claude API Fehler: {res.status_code} - {res.text}")

        elif provider == "ollama":
            base = (ollama_url or "http://localhost:11434").rstrip("/")
            url = f"{base}/api/chat"
            mod = model.strip() or "llama3"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": mod,
                "messages": messages,
                "stream": False
            }
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                return data["message"]["content"].strip()
            logger.warning(f"Ollama API Fehler: {res.status_code} - {res.text}")

    except Exception as e:
        logger.error(f"Fehler bei KI-Aufruf ({provider}): {e}")

    return None


def evaluate_safety_risk(
    title: str,
    price: Optional[float],
    description: str,
    seller_info: str = "",
    platform: str = "kleinanzeigen",
    ai_settings: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Erkennt typische Betrugs- und Scam-Muster (z.B. PayPal Freunde, Kurier-Tricks, Ausland).
    Kombiniert robuste heuristische Regelprüfung mit optionaler KI-Ergänzung.
    """
    text_corpus = f"{title}\n{description}\n{seller_info}".lower()
    flags = []
    risk_score = 5

    # 1. PayPal Freunde / ungesicherte Zahlung
    if re.search(r"paypal\s*(nur\s*)?(an\s*)?freunde|f&f|family\s*(&|and)\s*friends", text_corpus):
        flags.append("Verlangt explizit Zahlung per 'PayPal Freunde' (kein Käuferschutz)")
        risk_score += 45

    # 2. Kurier- und Speditionsmasche
    if re.search(r"kurier|spedition|fedex\s*bote|dpd\s*bote|bote\s*bringt\s*bargeld|geld\s*im\s*umschlag", text_corpus):
        flags.append("Verdacht auf Kurier-/Briefträger-Betrugsmasche (Geldübergabe an Boten)")
        risk_score += 50

    # 3. Geschenkkarten / Dampf / Steam
    if re.search(r"dampfkarte|steam\s*karte|gutscheinkarte|paysafecard", text_corpus):
        flags.append("Erwähnung von Gutschein-/Steam-Karten als Zahlungsmittel")
        risk_score += 50

    # 4. Ausland / atypische Kontaktaufnahme
    if re.search(r"befinde\s*mich\s*im\s*ausland|arbeit\s*auf\s*einer\s*ölplattform|schiffsingenieur|nur\s*per\s*e-?mail\s*antworten|kontakt\s*nur\s*über\s*whatsapp", text_corpus):
        flags.append("Typische Betrugsphrasen (Auslandsaufenthalt, Umleitung außerhalb der Plattform)")
        risk_score += 35

    # 5. Extrem niedriger Preis bei Luxus-/Technik-Artikeln
    if price is not None and price > 0:
        high_value_keywords = ["rtx 4090", "rtx 4080", "iphone 15 pro", "iphone 16 pro", "macbook m3", "ps5", "playstation 5", "sony a7 iv"]
        for kw in high_value_keywords:
            if kw in title.lower():
                if price < 150:
                    flags.append(f"Auffällig unrealistischer Schleuderpreis ({price:.2f} €) für {kw.upper()}")
                    risk_score += 40
                break

    # 6. Kein Versand und keine Abholung Widerspruch
    if "keine abholung" in text_corpus and "nur überweisung" in text_corpus:
        flags.append("Keine Abholung möglich und ausschließliche Überweisung gefordert")
        risk_score += 30

    risk_score = min(risk_score, 100)

    if risk_score >= 60:
        risk_level = "hoch"
        verdict = "Erhöhte Wachsamkeit geboten! Diese Anzeige weist deutliche Merkmale bekannter Betrugsmaschen auf."
    elif risk_score >= 30:
        risk_level = "mittel"
        verdict = "Einige Punkte genau prüfen. Nutzen Sie ausschließlich sichere Zahlungsmethoden oder Barzahlung bei Abholung."
    else:
        risk_level = "niedrig"
        verdict = "Keine auffälligen Betrugsmuster erkannt. Die Anzeige wirkt plausibel und unauffällig."

    tips = [
        "Niemals per 'PayPal Freunde & Familie' oder ungesicherte Banküberweisung zahlen.",
        "Am sichersten ist Barzahlung bei persönlicher Abholung und Ausprobieren des Artikels.",
        "Über 'Sicher Bezahlen' der Plattform ist Ihr Geld geschützt, bis das Paket ankommt."
    ]

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "flags": flags,
        "verdict": verdict,
        "safety_tips": tips
    }


def evaluate_deal_score(
    title: str,
    price: Optional[float],
    description: str,
    platform: str = "kleinanzeigen",
    min_budget: Optional[float] = None,
    max_budget: Optional[float] = None,
    peer_prices: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Berechnet einen Deal-Score (0-100) basierend auf Preis, Budgetgrenzen,
    Vergleichspreisen und Zustandsbeschreibungen.
    """
    if price is None:
        return {
            "score": 50,
            "label": "VB / Unbekannt",
            "verdict": "Kein Festpreis angegeben. Verhandlungsbasis oder Preis auf Anfrage.",
            "pros": ["Preis verhandelbar"],
            "cons": ["Kein fixer Betrag genannt"]
        }

    pros = []
    cons = []
    base_score = 65

    # Vergleich mit Suchgrenzen
    if max_budget and max_budget > 0:
        ratio = price / max_budget
        if ratio <= 0.6:
            base_score += 25
            pros.append(f"Deutlich unter deinem Maximalbudget von {int(max_budget)} €")
        elif ratio <= 0.8:
            base_score += 15
            pros.append("Günstig im Vergleich zu deinem Maximalbudget")
        elif ratio >= 1.05:
            base_score -= 20
            cons.append("Liegt leicht über deinem Zielbudget")

    # Zustand analysieren
    desc_low = (description or "").lower()
    if any(k in desc_low for k in ["neuwertig", "ovp", "originalverpackt", "ungeöffnet", "wie neu", "rechnung vorhanden", "garantie"]):
        base_score += 10
        pros.append("Zustand als neuwertig, OVP oder mit Rechnung/Garantie beschrieben")
    elif any(k in desc_low for k in ["defekt", "bastler", "beschädigt", "ersatzteil", "displaybruch", "geht nicht an"]):
        base_score -= 25
        cons.append("Hinweis auf Mängel, Defekt oder Bastlerware in der Beschreibung")

    if any(k in desc_low for k in ["zubehör", "inklusive", "gratis dazu", "extra"]):
        base_score += 5
        pros.append("Zusätzliches Zubehör oder Extras inklusive")

    # Vergleich mit anderen Angeboten
    if peer_prices and len(peer_prices) >= 2:
        valid_peers = [p for p in peer_prices if p and p > 0]
        if valid_peers:
            avg_peer = sum(valid_peers) / len(valid_peers)
            if price < avg_peer * 0.8:
                base_score += 15
                pros.append(f"Ca. {int((1 - price/avg_peer) * 100)}% günstiger als der Schnitt ähnlicher Angebote ({avg_peer:.0f} €)")
            elif price > avg_peer * 1.2:
                base_score -= 15
                cons.append(f"Liegt über dem Schnitt vergleichbarer Angebote ({avg_peer:.0f} €)")

    final_score = max(10, min(98, base_score))

    if final_score >= 85:
        label = "Top-Deal"
        verdict = "Hervorragendes Preis-Leistungs-Verhältnis. Schnelles Handeln empfohlen!"
    elif final_score >= 70:
        label = "Sehr gut"
        verdict = "Sehr faires und attraktives Angebot."
    elif final_score >= 50:
        label = "Fairer Preis"
        verdict = "Solides Angebot im üblichen Marktbereich."
    else:
        label = "Eher teuer"
        verdict = "Preislich eher am oberen Ende oder Zustand erfordert Preisnachlass."

    return {
        "score": final_score,
        "label": label,
        "verdict": verdict,
        "pros": pros,
        "cons": cons
    }


def generate_negotiation_reply(
    title: str,
    current_price: Optional[float],
    description: str,
    target_price: Optional[float],
    style: str = "freundlich",
    stop_condition: str = "",
    chat_history: Optional[List[Dict[str, str]]] = None,
    latest_seller_message: str = "",
    ai_settings: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Erstellt den nächsten Verhandlungsschritt / die nächste Nachricht an den Verkäufer.
    Prüft Abbruchkriterien und unterstützt KI-Modelle sowie intelligente Heuristik.
    """
    chat_history = chat_history or []
    style_desc = STYLE_PROMPTS.get(style, STYLE_PROMPTS["freundlich"])
    seller_msg_clean = (latest_seller_message or "").strip()

    # 1. Abbruchkriterien prüfen
    should_stop = False
    stop_reason = ""
    target_reached = False

    # Verkäufer akzeptiert Angebot
    if seller_msg_clean:
        seller_low = seller_msg_clean.lower()
        if any(w in seller_low for w in ["geht klar", "abgemacht", "können wir machen", "passt so", "kannst du haben", "einverstanden", "deal", "ist in ordnung"]):
            should_stop = True
            target_reached = True
            stop_reason = "Der Verkäufer hat deinem Preisvorschlag zugestimmt."

        # Verkäufer lehnt strikt ab
        if any(w in seller_low for w in ["festpreis", "kein cent weniger", "unter keinen umständen", "letzter preis", "wird nicht verhandelt", "nein danke"]):
            if stop_condition and any(sc in seller_low for sc in stop_condition.lower().split(",")):
                should_stop = True
                stop_reason = f"Abbruchbedingung erfüllt: Verkäufer verhandelt nicht weiter ('{seller_msg_clean}')."

    # Preischeck gegenüber Wunschpreis
    if current_price is not None and target_price is not None and target_price > 0:
        if current_price <= target_price:
            target_reached = True
            should_stop = True
            stop_reason = f"Der Angebotspreis ({current_price:.2f} €) liegt bereits auf oder unter deinem Wunschpreis ({target_price:.2f} €)."

    if should_stop:
        if target_reached:
            msg = (
                f"Hallo! Vielen Dank für die Zusage. Das freut mich sehr. "
                f"Wie wollen wir die Übergabe machen? Ich könnte den Artikel persönlich abholen oder per versichertem Versand übernehmen."
            )
            strategy = "Zielpreis erreicht: Verbindliche Zusage und Abhol-/Versanddetails klären."
        else:
            msg = "Vielen Dank für die Rückmeldung. Falls Sie es sich doch noch anders überlegen, melden Sie sich gerne. Viele Grüße!"
            strategy = f"Verhandlung beendet: {stop_reason}"

        return {
            "reply_text": msg,
            "strategy": strategy,
            "should_stop": True,
            "stop_reason": stop_reason,
            "target_reached": target_reached
        }

    # 2. KI versuchen, falls konfiguriert
    ai_settings = ai_settings or {}
    provider = ai_settings.get("ai_provider", "").strip().lower()
    api_key = ai_settings.get("ai_api_key", "").strip()

    if provider and provider not in ("heuristic", "none", "aus") and (api_key or provider == "ollama"):
        system_prompt = (
            "Du bist ein erfahrener Verhandlungsassistent für Online-Kleinanzeigen und Facebook Marketplace. "
            "Deine Aufgabe ist es, für den Käufer eine überzeugende, realistische und respektvolle Nachricht auf Deutsch zu formulieren, "
            f"um den Artikel '{title}' zum Zielpreis zu bekommen.\n\n"
            f"Gewählter Verhandlungsstil: {style_desc}\n"
            f"Zielpreis des Käufers: {target_price or 'Verhandlungssache'} €\n"
            f"Aktueller Angebotspreis: {current_price or 'Nicht angegeben'} €\n"
            f"Abbruchbedingung: {stop_condition or 'Keine besondere'}\n"
            "Regeln:\n"
            "- Schreibe NUR den Nachrichtentext, den der Käufer direkt abschicken kann.\n"
            "- Keine Begrüßungsfloskeln an den Benutzer ('Hier ist Ihr Text'), sondern direkt die Nachricht an den Verkäufer.\n"
            "- Bleibe natürlich, sympathisch und verhandle klug."
        )

        history_summary = "\n".join([f"{m.get('sender', 'user')}: {m.get('text', '')}" for m in chat_history])
        user_prompt = (
            f"Artikel: {title}\n"
            f"Beschreibung: {description[:500]}\n"
            f"Bisheriger Nachrichtenverlauf:\n{history_summary or 'Noch keine Nachrichten gesendet.'}\n\n"
            f"Letzte Nachricht des Verkäufers: '{seller_msg_clean or 'Noch keine Antwort'}'\n"
            "Formuliere den nächsten optimalen Verhandlungsschritt."
        )

        llm_reply = call_llm_api(
            provider=provider,
            api_key=api_key,
            model=ai_settings.get("ai_model", ""),
            prompt=user_prompt,
            system_prompt=system_prompt,
            ollama_url=ai_settings.get("ai_ollama_url", "http://localhost:11434")
        )

        if llm_reply:
            return {
                "reply_text": llm_reply,
                "strategy": f"Erstellt mit {provider.upper()} im Stil '{style}'.",
                "should_stop": False,
                "stop_reason": "",
                "target_reached": False
            }

    # 3. Intelligenter Heuristik-Generator (sofort einsatzbereit ohne API-Key)
    offer_price = target_price
    if not offer_price and current_price:
        offer_price = round(current_price * 0.85, 0)

    step_count = len([m for m in chat_history if m.get("sender") in ("user", "assistant")])

    if step_count == 0:
        # Erste Kontaktaufnahme
        if style == "freundlich":
            reply = (
                f"Guten Tag! Ich habe großes Interesse an Ihrer Anzeige '{title}'. "
                f"Ist der Artikel noch zu haben? Wäre für Sie ein Preis von {int(offer_price) if offer_price else 'einem kleinen Nachlass'} € "
                f"in Ordnung? Ich könnte zeitnah abholen oder die Versandkosten übernehmen. Viele Grüße!"
            )
            strat = f"Freundlicher Einstieg mit erstem Angebot bei {int(offer_price) if offer_price else 'Nachlass'} €."
        elif style == "sachlich":
            reply = (
                f"Hallo, ist der Artikel noch verfügbar? "
                f"Ich biete Ihnen {int(offer_price) if offer_price else ''} € bei zügiger Abwicklung an. "
                f"Passt das für Sie?"
            )
            strat = "Sachliches, direktes Angebot."
        elif style == "schnaeppchenjaeger":
            reply = (
                f"Hallo! Wenn der Artikel noch da ist, würde ich ihn für {int(offer_price) if offer_price else ''} € sofort nehmen "
                f"und heute noch per PayPal oder bei schneller Abholung bar bezahlen. Passt das?"
            )
            strat = "Fokus auf sofortige Zahlung / schnelle Abholung gegen Nachlass."
        else: # hartnaeckig
            reply = (
                f"Hallo, der Artikel interessiert mich. Mit Blick auf Zustand und aktuelle Vergleichsangebote "
                f"wären {int(offer_price) if offer_price else ''} € für mich ein faires Angebot. Können wir uns darauf einigen?"
            )
            strat = "Bestimmtes Angebot mit Verweis auf Vergleichspreise."
    else:
        # Folgeschritt nach Gegenangebot
        if offer_price and current_price and offer_price < current_price:
            counter = round((offer_price + current_price) / 2, 0)
        else:
            counter = offer_price

        if style == "freundlich":
            reply = (
                f"Vielen Dank für Ihre Antwort! Wie wäre es, wenn wir uns in der Mitte bei {int(counter) if counter else 'einem kleinen Kompromiss'} € "
                f"treffen? Dann hätten wir für beide Seiten eine faire Lösung."
            )
            strat = "Kompromissvorschlag in der Mitte."
        elif style == "sachlich":
            reply = (
                f"Danke für die Rückmeldung. Mein absolutes Limit wären {int(counter) if counter else ''} €. "
                f"Wenn das für Sie machbar ist, schließe ich den Kauf gerne direkt ab."
            )
            strat = "Klares oberes Limit gesetzt."
        else:
            reply = (
                f"Danke für die Nachricht. Bei {int(counter) if counter else ''} € würde ich direkt zusagen "
                f"und die Zahlung umgehend veranlassen."
            )
            strat = "Verbindliches finales Gegenangebot."

    return {
        "reply_text": reply,
        "strategy": strat,
        "should_stop": False,
        "stop_reason": "",
        "target_reached": False
    }
