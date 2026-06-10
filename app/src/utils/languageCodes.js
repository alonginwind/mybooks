export const languageCodes = {
    "zho": "中文",
    "zha": "繁體中文",
    "eng": "English",
    "fra": "French",
    "deu": "German",
    "spa": "Spanish",
    "rus": "Russian",
    "jpn": "Japanese",
    "ita": "Italian",
    "por": "Portuguese",
    "kor": "Korean",
    "nld": "Dutch",
    "ara": "Arabic",
    "mon": "Mongolian",
    "mnc": "满文",
    "bod": "Tibetan",
    "hin": "Hindi",
    "tur": "Turkish",
    "vie": "Vietnamese",
    "tha": "Thai",
    "ell": "Greek",
    "pol": "Polish"
};

export const languageOptions = Object.entries(languageCodes).map(([code, name]) => ({ code, name }));
