def assign_service(subject):
    text = subject.lower()

    if "médicament" in text or "pharmacie" in text:
        return "Pharmacie"
    elif "analyse" in text or "labo" in text:
        return "Laboratoire"
    elif "urgence" in text or "grave" in text:
        return "Urgence"
    return "Consultation"


def detect_priority(description):
    text = description.lower()
    urgent_words = ["grave", "urgence", "sang", "douleur", "critique"]
    for word in urgent_words:
        if word in text:
            return "Critique"
    return "Normale"