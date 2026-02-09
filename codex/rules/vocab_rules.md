# Norwegian Vocab Rules

Scope: TSV vocabulary data at repo root (topic files) and vocab/ copies.

## File layout
- One TSV per topic (e.g., `school.tsv`, `grocery_store.tsv`).
- Single header row:
  - lexical-category, english, norwegian, pronunciation, example_sentence
- Tab-separated fields; no embedded newlines inside any field.

## Entry patterns
- One entry per line after the header.
- `lexical-category` values: noun, verb, adjective, adverb, expression.
- `english`: lowercase phrase preferred; may include parenthetical clarifiers (e.g., "class (lesson)").
- English nouns should be singular unless there is a strong reason to use plural.
- `norwegian` patterns:
  - Noun: includes article `en/ei/et` (e.g., `en skole`).
  - Verb: `å <infinitive>, present, past, past perfect` (comma + space separated),
    e.g., `å lære, lærer, lærte, har lært`.
  - Other categories: plain Norwegian term or phrase.
- `pronunciation`: IPA for the infinitive/base form only; use slashes (e.g., `/ˈskuːlə/`).
- `example_sentence`: full Norwegian sentence that matches the entry term/form.

## Consistency checks
- All topic files must share the same header and column order.
- Every noun must start with `en`, `ei`, or `et` in the Norwegian field.
- Every verb must contain exactly four comma-separated forms.
- Keep format uniform across files (spacing after commas, slashes around IPA).

## When editing translations
- Update the example sentence to align with the updated Norwegian term.
- Preserve the one-line, tab-separated format.
