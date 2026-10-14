from thefuzz import fuzz

# Watchlist for KYB (Entities)
WATCHLIST_ENTITIES = [
    {"name": "ACME GLOBAL CORP", "category": "Sanctioned Entity", "country": "RU"},
    {"name": "SHADY HOLDINGS LLC", "category": "Blocked Entity", "country": "KP"}
]

# Watchlist for KYC (Individuals)
WATCHLIST_INDIVIDUALS = [
    {"name": "VICTOR V. VANCE", "dob": "1985-04-12", "category": "Politically Exposed Person (PEP)", "country": "CY"},
    {"name": "DMITRY V. IVANOV", "dob": "1972-09-23", "category": "SDN Sanctioned Individual", "country": "RU"}
]

def screen_entity_name(query_name: str, threshold: int = 85):
    best_match = None
    highest_score = 0

    for entry in WATCHLIST_ENTITIES:
        score = fuzz.token_set_ratio(query_name.upper(), entry["name"])
        if score > highest_score:
            highest_score = score
            best_match = entry

    if highest_score >= threshold:
        return {
            "flagged": True,
            "confidence_score": highest_score,
            "matched_entity": best_match["name"],
            "category": best_match["category"],
            "country": best_match["country"]
        }
    
    return {"flagged": False, "confidence_score": highest_score, "matched_entity": None}

def screen_individual_person(full_name: str, dob: str = None, country: str = None, threshold: int = 85):
    best_match = None
    highest_score = 0

    for entry in WATCHLIST_INDIVIDUALS:
        score = fuzz.token_set_ratio(full_name.upper(), entry["name"])
        if score > highest_score:
            highest_score = score
            best_match = entry

    if highest_score >= threshold:
        return {
            "flagged": True,
            "confidence_score": highest_score,
            "matched_name": best_match["name"],
            "matched_dob": best_match["dob"],
            "category": best_match["category"],
            "country": best_match["country"]
        }
    
    return {"flagged": False, "confidence_score": highest_score, "matched_name": None}