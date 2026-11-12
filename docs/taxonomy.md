# Item↔Lean classification (shared by every mapping, verifying, judging and skeptic agent)

Adapted from the ternary Goldbach companion's `TAXONOMY.md`. There the text was a book
formalized afterwards; here the text, "[M]", is a manuscript written from the Lean, "[L]", and
claims that it states nothing [L] does not prove. Every judgment answers one question: **does [L]
prove what [M] prints here?** The book-only fields (role in the book's proof, literature,
changes since 2013) are dropped.

## Sources

- [M]: `~/ym-companion/src/manuscript/` (`main.tex`, `macros.tex`, `part1/*.tex`, `part2/*.tex`)
  at `1a47ac9`. Macros are in `macros.tex`; read them when a symbol matters.
- [L]: `~/ym-companion/lean/` at `3456e5e`. Not built. Read the source; trust the Lean statement
  over its docstring.
- [M]'s own map of [L], evidence of where to look and never of what is true:
  `src/data/key-statements.tsv`, `src/data/declaration-units.tsv`, `src/outline/units/*.md`,
  `src/glossary.md`, `src/statement.md`.
- Tool: `python3 ~/ym-companion/repo/scripts/mapping/tool.py help` (`batch`, `item`, `tex`,
  `decl`, `search`, `keys`, `exists`, `check`). Use `grep -rn` in `~/ym-companion/lean/YM` freely.

## Rules

1. Read-only everywhere except your own output file. Never run `lake`, never build.
2. Every declaration you name is fully qualified and passes `tool.py exists`.
3. Compare statements, not names or summaries. Read the Lean signature and hypotheses in full,
   including section `variable`s and the definitions they use, before choosing a status.
4. A status of `no-match` needs a real search: names, key statements, outline units, and greps for
   the item's distinctive symbols and constants. Record the searches in `searched`.
5. Own words in `note`, one or two sentences, premises before conclusions. No hedges.

## Status

| status | meaning | finding? |
|---|---|---|
| `exact` | A declaration states the item: same hypotheses and conclusion, same constants, up to notation, encoding (ℕ/ℝ casts, `Finset` sums, bundled structures) and junk values. | no |
| `close` | Same claim with differences a reader should know (a normalization, a closed vs open range, an unfolded definition, the item's constants named abstractly in [L] where [M] says "some constant"), and no direction of strength. | no |
| `stronger` | [L] proves more than [M] prints: weaker hypotheses or a stronger conclusion. | no |
| `parts` | No single declaration states the item, but listed key declarations each state one of its claims, and together they state all of it. | no |
| `inlined` | A step (usually a display inside a proof) that has no standalone declaration but is proved inside a named declaration's proof. Give that declaration and the `file:line` range of the step. | no |
| `definition-match` | A definition that agrees with [L]'s. | no |
| `definition-close` | A definition that agrees up to differences a reader should know (an equivalent but differently packaged condition, a normalization). | no |
| `not-formalized-not-needed` | The item asserts no mathematics [L] could prove: motivation, heuristics marked as such, notation, a summary sentence pointing to other items, a classical result outside [L]'s scope that [M] cites as literature. Say why. | no |
| `weaker` | [L] proves the item's shape but less: a worse constant, a narrower range, a weaker conclusion. Say which. | **yes** |
| `missing-hypothesis` | [L]'s declaration needs a hypothesis that [M]'s statement (with its standing assumptions in the section) omits. Name it. | **yes** |
| `differs` | [L] proves a different claim that plays the item's role, and neither implies the other; or a definition of [M] disagrees with [L]'s (`definition-differs` is written `differs`). | **yes** |
| `no-match` | The item asserts mathematics and [L] holds no counterpart, alone or in parts, after a real search; also when only some of the item's claims are in [L] (say which are missing). | **yes** |
| `unclear` | You could not decide. Say what blocks the decision. | — |

Before claiming a finding, look for what would refute it: the hypothesis supplied by a
structure field, a section `variable`, a definition's body, or [M]'s standing assumptions; the
stronger claim proved under another name; a constant fixed elsewhere. [M] fixes conventions at the
start of sections and in Section 3/Appendix; a hypothesis stated there is not missing.

## Roles of declarations (`lean[].role`)

| role | meaning |
|---|---|
| `key` | states the item (or, for `parts`, one of its claims; for `inlined`, contains the step in its proof) |
| `attributed` | [M]'s map (outline, key statements) attributes the item to it, and it is relevant, but it is not what states the item |
| `support` | a definition or structure the item's statement is read through, or a lemma that states a hypothesis or an ingredient |
| `helper` | a lemma used in the proof of the key declaration that carries a step the item mentions |

## Status → relation (subject: [M]'s item; object: the Lean declaration)

Direction follows Literature Links: `broadMatch` says the object ([L]) is more general,
`narrowMatch` that the subject ([M]) is.

| status | key link | other links |
|---|---|---|
| `exact`, `definition-match` | `exactMatch` | `relatedMatch` |
| `close`, `definition-close` | `closeMatch` | `relatedMatch` |
| `stronger` | `broadMatch` | `relatedMatch` |
| `weaker`, `missing-hypothesis` | `narrowMatch` | `relatedMatch` |
| `parts` | `hasPart` on each key link | `relatedMatch` |
| `inlined` | `relatedMatch` | `relatedMatch` |
| `differs` | `relatedMatch` | `relatedMatch` |
| `no-match`, `not-formalized-not-needed` | `noMatch` against the repository at the pin | — |
| `unclear` | none | none |

A `no-match` item that has partial or related declarations links them with `hasPart` or
`relatedMatch` as well.

## Output (one JSON file per batch)

```json
{
  "batch": "S13-1",
  "agent": "mapper | verifier | judge",
  "items": [
    {
      "id": "Lemma 13.4",
      "status": "exact",
      "lean": [
        {"decl": "YM.Fully.Qualified.name", "role": "key", "where": "YM/Path/File.lean:120-140",
         "note": "what this declaration contributes, if not obvious"}
      ],
      "note": "One or two sentences on what differs, premises first.",
      "step": "for a display in a proof: the declaration whose proof contains the step, or the lemma that states it, with file:line",
      "searched": ["names, greps and key statements searched, for no-match / not-formalized-not-needed"],
      "confidence": "high | medium | low"
    }
  ]
}
```

Run `python3 ~/ym-companion/repo/scripts/mapping/tool.py check <file>` and fix every error before
you finish.
