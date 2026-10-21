"""WikiData relation identifiers, taken from RippleEdits.

Used verbatim from the reference implementation at
https://github.com/edenbiran/RippleEdits (MIT; licence text reproduced in THIRD_PARTY_LICENSES.md). Paper:
Cohen, R., Biran, E., Yoran, O., Globerson, A. and Geva, M. (2024) 'Evaluating the
ripple effects of knowledge editing in language models', Transactions of the
Association for Computational Linguistics (TACL). arXiv:2307.12976.

Both the `wiki_relations` mapping and the `Ripple_Relation` enum are the reference's,
reused so that Genie addresses the same WikiData properties as RippleEdits and the two
benchmarks stay comparable.
"""

from enum import Enum


# Verbatim from the RippleEdits reference implementation.
wiki_relations = {
    'head of government': 'P6',
    'brother': 'P7',
    'sister': 'P9',
    'sibling': 'P3373',
    'country': 'P17',
    'place of birth': 'P19',
    'place of death': 'P20',
    'sex or gender': 'P21',
    'father': 'P22',
    'mother': 'P25',
    'spouse': 'P26',
    'country of citizenship': 'P27',
    'continent': 'P30',
    'head of state': 'P35',
    'capital': 'P36',
    'currency': 'P38',
    'position held': 'P39',
    'official language': 'P37',
    'child': 'P40',
    'stepfather': 'P43',
    'stepmother': 'P44',
    'author': 'P50',
    'member of sports team': 'P54',
    'director': 'P57',
    'screenwriter': 'P58',
    'alma mater': 'P69',
    'architect': 'P84',
    'composer': 'P86',
    'anthem': 'P85',
    'sexual orientation': 'P91',
    'editor': 'P98',
    'occupation': 'P106',
    'employer': 'P108',
    'founder': 'P112',
    'league': 'P118',
    'place of burial': 'P119',
    'field of work': 'P101',
    'native language': 'P103',
    'cast member': 'P161',
    'award received': 'P166',
    'follows': 'P155',
    'ethnic group': 'P172',
    'religion': 'P140',
    'eye color': 'P1340',
    'capital of': 'P1376',
    'number of children': 'P1971',
    'uncle': '',
    'aunt': '',
    'date of birth': 'P569',
}


# Verbatim from the RippleEdits reference implementation.
class Ripple_Relation(Enum):

    # Subject is a person
    MOTHER = ('P25', 'The name of the mother of <subject> is', ['BROTHER', 'SISTER', 'SIBLING', 'UNCLE', 'AUNT'], True)
    FATHER = ('P22', 'The name of the father of <subject> is', ['BROTHER', 'SISTER', 'SIBLING', 'UNCLE', 'AUNT'], True)
    BROTHER = ('P7', 'The name of the brother of <subject> is', ['SIBLING'], False)
    SISTER = ('P9', 'The name of the sister of <subject> is', ['SIBLING'], False)
    SIBLING = ('P3373', "The names of the siblings of <subject> are", ['BROTHER', 'SISTER'], False)
    SPOUSE = ('P26', "The name of the spouse of <subject> is", [], False)
    UNCLE = ('', 'The name of the uncle of <subject> is', [], False)
    AUNT = ('', 'The name of the aunt of <subject> is', [], False)
    CHILD = ('P40', 'The name of the child of <subject> is', ['NUMBER_OF_CHILDREN'], False)
    NUMBER_OF_CHILDREN = ('P1971', 'The number of children <subject> has is', [], True)
    PLACE_OF_BIRTH = ('P19', 'The place of birth of <subject> is', [], True)
    PLACE_OF_DEATH = ('P20', 'The place of death of <subject> is', ['is alive'], True)
    PLACE_OF_BURIAL = ('P119', 'The place of burial of <subject> is', ['is alive'], True)
    COUNTRY = ('P17', 'The name of the country which <subject> is associated with is',
               ['continent', 'official language', 'capital of', 'currency'], True)
    COUNTRY_OF_CITIZENSHIP = ('P27', 'The name of the country of citizenship of <subject> is', [], False)
    POSITION_HELD = ('P39', 'The name of the position held by <subject> is', [], False)
    STEPFATHER = ('P43', 'The name of the stepfather of <subject> is', ['number of children'], True)
    STEPMOTHER = ('P44', 'The name of the stepmother of <subject> is', [], True)
    MEMBER_OF_SPORTS_TEAM = ('P54', 'The name of the sports team which <subject> is a member of is', [], False)
    ALMA_MATER = ('P69', 'The name of the alma mater of <subject> is', [], False)
    OCCUPATION = ('P106', 'The occupation of <subject> is', ['field of work'], False)
    EMPLOYER = ('P108', "The name of the employer of <subject> is", [], False)
    LEAGUE = ('P118', 'The name of the league which <subject> plays in is', [], False)
    FIELD_OF_WORK = ('P101', 'The name of the field of work of <subject> is', ['occupation'], False)
    NATIVE_LANGUAGE = ('P03', 'The mother tongue of <subject> is', [], False)
    AWARD_RECEIVED = ('P166', 'The name of the award <subject> won is', [], False)
    FOLLOWS = ('P155', '<subject> follows', [], True)
    FOLLOWED_BY = ('P156', '<subject> is followed by', [], True)
    RELIGION = ('P140', 'The name of the religion which <subject> is associated with is', [], False)
    DATE_OF_BIRTH = ('P569', 'The date of birth of <subject> is', [], True)
    DATE_OF_DEATH = ('P570', 'The date of death of <subject> is', ['is alive'], True)
    IS_ALIVE = ('', 'Is <subject> still alive?', ['place of death', 'place of burial', 'date of death'], True)

    # Subject is a country
    HEAD_OF_GOVERNMENT = ('P6', 'The name of the head of government of <subject> is', ['head of state'], False)
    HEAD_OF_STATE = ('P35', 'The name of the head of state of <subject> is', ['head of government'], False)
    CONTINENT = ('P30', 'The name of the continent which <subject> is part of is', ['country'], True)
    CAPITAL = ('P36', 'The name of the capital city of <subject> is', [], True)
    CURRENCY = ('P38', 'The name of the currency in <subject> is', [], False)
    OFFICIAL_LANGUAGE = ('P37', 'The official language of <subject> is', [], False)
    ANTHEM = ('P85', 'The name of the anthem of <subject> is', [], True)
    LIKELY_ANTHEM = ('', 'The name of the anthem that is most likely to be performed in <subject> is', [], True)

    # Subject is a city
    CAPITAL_OF = ('P1376', 'The name of the country which <subject> is the capital of is',
                  ['country', 'continent', 'currency', 'official language', 'anthem'], True)

    # Subject is a book
    AUTHOR = ('P50', 'The name of the author of <subject> is', [], False)
    EDITOR = ('P98', 'The name of the editor of <subject> is', [], False)

    # Subject is a movie
    DIRECTOR = ('P57', 'The name of the director of <subject> is', [], False)
    SCREENWRITER = ('P58', 'The name of the screenwriter of <subject> is', [], False)
    CAST_MEMBER = ('P161', "The names of the cast members of <subject> are", [], False)

    # Subject is a building
    ARCHITECT = ('P84', 'The name of the architect of <subject> is', [], False)

    # Subject is a musical piece
    COMPOSER = ('P86', 'The name of the composer of <subject> is', [], False)

    # Subject is a company
    FOUNDER = ('P112', 'The name of the founder of <subject> is', [], False)

    CREATOR = ('P170', 'The name of the creator of <subject> is', [], False)
    DEVELOPER = ('P178', 'The name of the developer of <subject> is', [], False)
    PUBLISHER = ('P123', 'The name of the publisher of <subject> is', [], False)
    PRODUCTION_COMPANY = ('P272', 'The name of the production company of <subject> is', [], False)
    GENRE = ('P136', 'The genre of <subject> is', [], False)
    NARRATIVE_LOCATION = ('P840', 'The narrative location of <subject> is', [], True)
    HEADQUARTERS = ('P159', 'The headquarters of <subject> is located in', [], True)

    def __init__(self, relation_id, phrase, impacted_relations, is_modification):
        self._relation_id = relation_id
        self._phrase = phrase
        self._impacted_relations = impacted_relations
        self._is_modification = is_modification

    def id(self):
        return self._relation_id

    def phrase(self, subject):
        if isinstance(subject, list):
            if subject:
                subject = subject[0]
            else:
                return self._phrase
        return self._phrase.replace('<subject>', subject)

    # def evaluate(self, subject):
    #     return subject_relation_to_targets(subject, self._relation_id)

    def impacted_relations(self):
        return [self.string_to_enum(r) for r in self._impacted_relations]

    def is_modification(self):
        return self._is_modification

    def formal_name(self):
        return self.name.lower().replace('_', ' ')