# -*- coding: utf-8 -*-
"""Shared fixtures for the trainer test suite."""


def make_verb(infinitive="aller", translation="to go", group="ir_irregular",
              auxiliary="\u00eatre", present=None, pc_masc=None, pc_fem=None,
              notes=None):
    """Build a spec-valid verb dict. 'present' also fills the simple tenses."""
    present = present or ["f1", "f2", "f3", "f4", "f5", "f6"]
    pc_masc = pc_masc or ["ai " + present[0], "as " + present[0], "a " + present[0],
                          "avons " + present[0], "avez " + present[0], "ont " + present[0]]
    tenses = {
        "present": {"label": "pr\u00e9sent", "type": "simple", "forms": list(present)},
        "imparfait": {"label": "imparfait", "type": "simple", "forms": list(present)},
        "futur_simple": {"label": "futur simple", "type": "simple", "forms": list(present)},
        "futur_proche": {"label": "futur proche", "type": "periphrastic",
                         "forms": ["vais " + infinitive, "vas " + infinitive, "va " + infinitive,
                                   "allons " + infinitive, "allez " + infinitive, "vont " + infinitive]},
        "conditionnel": {"label": "conditionnel", "type": "simple", "forms": list(present)},
        "pass\u00e9_compos\u00e9": {"label": "pass\u00e9 compos\u00e9", "type": "compound",
                                    "forms": list(pc_masc)},
    }
    if pc_fem is not None:
        tenses["pass\u00e9_compos\u00e9"]["feminine"] = list(pc_fem)
    verb = {"infinitive": infinitive, "translation": translation, "group": group,
            "auxiliary": auxiliary, "tenses": tenses}
    if notes is not None:
        verb["notes"] = notes
    return verb


ALLER_PRESENT = ["vais", "vas", "va", "allons", "allez", "vont"]
ALLER_PC = ["suis all\u00e9", "es all\u00e9", "est all\u00e9",
            "sommes all\u00e9s", "\u00eates all\u00e9s", "sont all\u00e9s"]
ALLER_PC_FEM = ["suis all\u00e9e", "es all\u00e9e", "est all\u00e9e",
                "sommes all\u00e9es", "\u00eates all\u00e9es", "sont all\u00e9es"]

VALID_AVOIR_VERB = make_verb(
    infinitive="finir", translation="to finish", group="ir_regular", auxiliary="avoir",
    present=["finis", "finis", "finit", "finissons", "finissez", "finissent"],
    pc_masc=["ai fini", "as fini", "a fini", "avons fini", "avez fini", "ont fini"],
)

VALID_ETRE_VERB = make_verb(
    infinitive="aller", translation="to go", group="ir_irregular", auxiliary="\u00eatre",
    present=ALLER_PRESENT, pc_masc=ALLER_PC, pc_fem=ALLER_PC_FEM,
)
