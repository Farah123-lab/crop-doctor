# crops.py - common crops in Somalia, with their Somali names
# Format:  "English name": "Somali name"
# You can add more crops here. Check each Somali name with a farmer or expert.

CROPS = {
    "Maize": "Galley",
    "Sorghum": "masago",
    "Rice": "Bariis",
    "Tomato": "Yaanyo",
    "Onion": "Basal",
    "Potato": "Baradho",
    "Banana": "Moos",
    "Mango": "Cambe",
    "Papaya": "Babaay",
    "Lemon": "Liin",
    "Watermelon": "qare",
    "Cowpea": "Digir",
    "Cassava": "Moxog",
    "Date palm": "Timir",
    "Sesame": "Sisin",
    "Okra": "Bamiya",
    "Pepper": "Basbaas",
}


def crops_text():
    # Make one short text the AI can read
    pairs = [english + " = " + somali for english, somali in CROPS.items()]
    return (
        "Common crops in Somalia (English = Somali): "
        + ", ".join(pairs)
        + ". When you name a crop, use its Somali name."
    )