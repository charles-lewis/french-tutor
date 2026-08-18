# French Tutor

Two local Python CLI tools for drilling French:

- **Verb Trainer** — drills full conjugations across six tenses with weighted spaced repetition
- **Vocabulary Trainer** — drills French↔English word meanings (nouns, adjectives, adverbs, phrases)

## Requirements

Python 3.8+

No external packages required.

## Running

From the project directory:

```
# Verb trainer
python train.py

# Vocabulary trainer
python vocab.py
```

Or use the Windows batch files: `run_verb_tutor.cmd` / `run_vocab_tutor.cmd`

## Inline Commands

Both trainers accept these commands at any prompt:

| Command   | Function                                   |
|-----------|--------------------------------------------|
| `:help`   | List all commands                          |
| `:quit`   | Show session report, save progress, exit   |
| `:skip`   | Skip this prompt (counted as incorrect)    |
| `:reveal` | Show the answer (counted as incorrect)     |
| `:new`    | Return to session setup                    |
| `:tenses` | Change tense scope (verb trainer only)     |
| `:stats`  | Show session + per-item stats              |

## Data Files

All data files live in `data/`.

### Verb Trainer

| File            | Description                                         |
|-----------------|-----------------------------------------------------|
| `verbs.json`    | Verb conjugation dataset (54 verbs, 6 tenses each)  |
| `progress.json` | Per-item progress (auto-created, tracks learning)   |
| `config.json`   | Persisted session settings (tense scope)            |

### Vocabulary Trainer

| File                | Description                                 |
|---------------------|---------------------------------------------|
| `vocab_apartment.json` | Themed vocabulary set (apartment/renting)  |
| `vocab_progress.json`  | Per-item progress (auto-created)           |
| `vocab_config.json`    | Persisted session settings and data paths  |

## Data Formats

### verbs.json

```json
{
  "verbs": [
    {
      "infinitive": "venir",
      "translation": "to come",
      "group": "ir_irregular",
      "auxiliary": "être",
      "tenses": {
        "present": {
          "label": "présent",
          "type": "simple",
          "forms": ["viens", "viens", "vient", "venons", "venez", "viennent"]
        },
        "passé_composé": {
          "label": "passé composé",
          "type": "compound",
          "forms": ["suis venu", "es venu", "est venu", "sommes venus", "êtes venus", "sont venus"],
          "feminine": ["suis venue", "es venue", "est venue", "sommes venues", "êtes venues", "sont venues"]
        }
      }
    }
  ]
}
```

Each verb must provide all six tenses: `present`, `imparfait`, `futur_simple`, `futur_proche`, `conditionnel`, `passé_composé`.

- **`forms`** — always 6 entries, one per person (je, tu, il/elle, nous, vous, ils/elles)
- **`feminine`** — required on `passé_composé` for être-verbs only; forbidden elsewhere
- **`type`** — one of `simple`, `compound`, or `periphrastic`
- **`group`** — one of: `er_regular`, `re_regular`, `ir_regular`, `re_irregular`, `ir_irregular`, `irregular`
- **`auxiliary`** — `être` or `avoir`

### Vocabulary entries (vocab_apartment.json)

```json
{
  "entries": [
    {
      "id": "le_bail",
      "fr": "le bail",
      "en": ["the lease"],
      "pos": "noun",
      "notes": "masculine noun; plural les baux"
    }
  ]
}
```

- **`id`** — unique identifier
- **`fr`** — French word or phrase
- **`en`** — one or more accepted English meanings
- **`pos`** — part of speech: `noun`, `verb`, `adjective`, `adverb`, `phrase`
- **`notes`** — optional usage notes (shown after correct answers, never scored)

### Progress files (progress.json / vocab_progress.json)

Auto-managed by the trainers. Keys are:

- Verb trainer: `{infinitive}|{tense}|{person_index}` (e.g. `venir|present|0`)
- Vocabulary trainer: `{id}|{direction}` (e.g. `le_bail|fr2en`)

Each entry tracks success/failure counts, streak, last result, and recent response times.

## Testing

```
python -m unittest discover tests -v
```
