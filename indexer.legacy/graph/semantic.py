import spacy
from nltk.corpus import wordnet as wn


def extract_nouns(text: str) -> list[str]:
    """Extract nouns from text using spaCy."""
    print("[SEMANTIC] - input text -- ", text)
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    nouns = []
    for token in doc:
        if token.pos_ in ("NOUN", "PROPN"):
            nouns.append(token.text.lower())
    print("[SEMANTIC] - extracted nouns ", nouns)
    return nouns


def lineage(words: list[str]) -> dict[str, list[str]]:
    """Get the longest lineage path for each word in the list.
    Returns a dictionary mapping the original word to its lineage path.
    """
    lineages_map = {}
    for word in words:
        # Get all synsets for the word (noun)
        synsets = wn.synsets(word, pos=wn.NOUN)
        if not synsets:
            continue

        longest_path = []
        for synset in synsets:
            paths = synset.hypernym_paths()
            if paths:
                # Find the longest hypernym path for this synset
                current_longest = max(paths, key=len)
                if len(current_longest) > len(longest_path):
                    longest_path = current_longest

        if longest_path:
            # Extract lemma names
            path_lemmas = [s.lemmas()[0].name() for s in longest_path]
            # De-duplicate contiguous identical lemmas or similar cleanups if needed
            lineages_map[word] = path_lemmas

    return lineages_map
