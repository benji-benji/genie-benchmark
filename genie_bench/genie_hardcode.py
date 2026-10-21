

PARAPHRASES = {
"PARAPHRASE_1": {
"work":   "{subject} is a {subject_class} with its {relation} listed as",
"place":  "{subject} is a {subject_class} with its {relation} documented as",
"org":    "{subject} is a {subject_class} that has its {relation} listed as",
"person": "Biographical sources give {subject}'s {relation} as",
},
"PARAPHRASE_2": {
"work": "Although many details exist about {subject}, the primary {relation} is recognized as",
"person": "When historical records document the life of {subject}, the specific {relation} is noted as",
"place": "As one reads the geographic literature concerning {subject}, the applicable {relation} is identified as",
"org": "If we investigate the corporate and institutional background of {subject}, the {relation} is"
},
"PARAPHRASE_3": {
"work": "Upon a comprehensive review of the documented historical and production archives surrounding {subject}, the officially designated {relation} is established as",
"person": "Following an extensive examination of the public and genealogical records pertaining to {subject}, the corresponding {relation} is ultimately identified as",
"place": "In accordance with the stringent geopolitical and historical classifications maintained for {subject}, the officially designated {relation} is currently recorded as",
"org": "During a thorough examination of the administrative registries associated with {subject}, the primary {relation} was definitively identified as"
}
}

HOP        = "The {chain} of the {relation} of {subject} is"


ABSTRACT_1 = "Which of {a} and {b} has the same {relation} as {subject}? The answer is"

ABSTRACT_2 = {
    "work":   "{subject} is a {year} {subject_class}. Its {frame}",
    "place":  "{subject} is a {subject_class}. Its {frame}",
    "org":    "{subject} is a {subject_class} founded in {year}. Its {frame}",
    "person": "{subject} was born in {year}. {subject}'s {frame}",
}

ABSTRACT_3 = {
    "work":  "{subject_class} from {year} are often remembered for their {frame}. One example",
    "place": "{subject_class} are often remembered for their {frame}. One example",
    "org":   "{subject_class} founded in {year} are often remembered for their {frame}. One example",
}

ABSTRACT_3_PERSON = {
    "work":  "{person} {subject_class} from {year} are often remembered for their {frame}. One example",
    "place": "{person} {subject_class} are often remembered for their {frame}. One example",
    "org":   "{person} {subject_class} founded in {year} are often remembered for their {frame}. One example",
}

ABSTRACT_2_PERSON = {
    "work":   "{subject} is a {year} {person} {subject_class}. Its {frame}",
    "place":  "{subject} is a {person} {subject_class}. Its {frame}",
    "org":    "{subject} is a {person} {subject_class} founded in {year}. Its {frame}",
    "person": "{subject} was born in {year}. {subject}'s {frame}",
}

ABSTRACT_3_MIN_SITELINKS = 31

FRAMES = {  "composer": "music",
            "country of citizenship": "background",
            "genre": "classification",
            "place of birth": "early life",
            "country": "geography",
            "director": "production",
            "spouse": "personal life",
            "creator": "creation",
            "religion": "themes",
            "followed by": "legacy",
            "father": "family",
            "mother": "family",
            "author": "writing",
            "screenwriter": "script development",
            "sibling": "relatives",
            "field of work": "career",
            "follows": "franchise",
            "currency": "economy",
            "anthem": "national symbols",
            "production company": "financial backing",
            "developer": "development",
            "alma mater": "education",
            "award received": "accolades",
            "official language": "culture",
            "occupation": "professional life",
            "continent": "geography",
            "publisher": "distribution",
            "head of government": "leadership",
            "narrative location": "setting",
            "place of burial": "death",
            "child": "descendants",
            "founder": "origins",
            "architect": "design",
            "position held": "public life",
            "place of death": "death",
            "headquarters": "operations",
            "employer": "career",
            "member of sports team": "playing career",
            "capital": "government",
            "league": "competition",
            "head of state": "leadership",
            "cast member": "casting",
            "editor": "publication"
            }



DISCURSIVE_FRAMES = {
    "person": ["biography", "career", "early life", "family", "legacy", "influences"],
    "work":   ["history", "production", "reception", "style", "legacy"],
    "place":  ["history", "geography", "culture", "economy", "significance"],
    "org":    ["history", "founding", "significance"],
}
RELATION_TO_FRAME = {
    **{r: "work" for r in ("author", "editor", "director", "screenwriter",
                           "cast member", "composer", "architect", "creator",
                           "developer", "publisher", "production company",
                           "genre", "narrative location")},
    **{r: "place" for r in ("head of government", "head of state", "continent",
                            "capital", "currency", "official language", "anthem",
                            "capital of")},
    **{r: "org" for r in ("founder", "headquarters")},
}

RELATION_DISPLAY = {
    "award received": "award",
    "followed by":    "sequel",
    "follows":        "predecessor",
    "position held":  "position",
}

CLASS_TO_FRAME = {
    "Q5": "person",
    **{q: "work" for q in ("Q11424", "Q3305213", "Q7889", "Q7725634",
                           "Q105543609", "Q23691", "Q202866", "Q58483083",
                           "Q1002697",    # periodical
                             "Q21191270",   # television series episode
                             "Q104438958",  # lost painting
                             "Q112144412",  # esports discipline
                             "Q3658341")},  # literary character                      
    **{q: "place" for q in ("Q3624078", "Q3336843", "Q7275", "Q11303", "Q43113623", 
                            "Q41176",      # building
                             "Q1076486")}, # sports venue
    "Q4830453": "org", **{q: "org"    for q in ("Q891723",     # public company
                                 "Q786820",     # automobile manufacturer
                                 "Q10429667",   # car brand
                                 "Q1107679",    # animation studio
                                 "Q18127",      # record label
                                 "Q7278",       # political party
                                 "Q245065",     # intergovernmental organization
                                 "Q103229495",  # men's association football team
                                 "Q4498974",    # ice hockey team
                                 "Q47443726")}, # recurring tennis tournament
}


YEAR_PIDS = ["P577", "P571", "P569"]   # publication, inception, date of birth
PLACE_PIDS = ["P495", "P17", "P19"]
HOP_PIDS = ["P19", "P36", "P106", "P159", "P17", "P30"]
HOP_NAMES = {"P19": "place of birth", "P36": "capital", "P106": "occupation",
             "P159": "headquarters", "P17": "country", "P30": "continent"}
CUTOFF = 2018                          # GPT-2-XL's data stops at Dec 2017
