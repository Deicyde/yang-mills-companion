# Mapping proof steps and displays to [L]

Shared by every mapper, verifier and judge agent of the steps campaign. The first campaign mapped
[M]'s numbered items to [L] (`data/mapping.json`, by `docs/taxonomy.md`). This one maps the smaller
pieces: every **step** of every proof, and every unnumbered **display outside a proof**. For each
record the question is: **where does [L] carry this, and does it establish the same fact?**

## Sources

Paths are relative to the workspace `~/ym-companion`.

- [M]: `src/manuscript/` (`macros.tex`, `part1/*.tex`, `part2/*.tex`) at `1a47ac9`.
- [L]: `lean/` at `3456e5e`. Not built; never run `lake`. Read the source and trust the Lean
  statement over its docstring.
- [M]'s map of [L], evidence of where to look and never of what is true:
  `src/data/key-statements.tsv`, `src/outline/units/*.md`, `src/glossary.md`.
- Tools:
  - `python3 repo/scripts/steps/stool.py batch <B>`: the records, and for each enclosing item the
    first campaign's verdict and key declarations with line ranges. Start there.
  - `stool.py src <decl> [a b]`: a declaration's source with line numbers, headed by its range.
  - `stool.py range <decl>...`: ranges. `stool.py check <file>`: validate your output.
  - `python3 repo/scripts/mapping/tool.py tex <file> <a> <b>` ([M] lines), `search <regex>`
    (declaration names), `keys <regex>` (key statements); `grep -rn` in `lean/YM` and `lean/*.lean`.

## How to work

1. Run `stool.py batch <B>`. Read the proof (or the section) around the records in [M]'s LaTeX
   with `tool.py tex`, so that you know what each step claims in context.
2. Read the enclosing item's key declarations in full (`stool.py src`), then the lemmas their
   proofs call. A step is usually carried by a `have`/`obtain`/`calc` line of the key proof, or by
   a helper lemma the proof calls (then link the helper's statement lines), or by a lemma further
   down. Follow names: `grep -rn "lemma <name>\b\|theorem <name>\b\|def <name>\b" lean/YM`.
3. Then search more widely (names, key statements, greps for the step's distinctive symbols and
   constants such as `23/20`, `7/16`).
4. Compare what the lines establish with what the step claims, then choose the relation.

## Relation (subject: the step or display; object: the Lean lines)

| relation | the lines... |
|---|---|
| `exactMatch` | establish the same fact, up to notation, encoding and junk values |
| `closeMatch` | establish the same fact up to a difference a reader should know; the note names it |
| `broadMatch` | establish more: the Lean is more general (weaker hypotheses or stronger conclusion) |
| `narrowMatch` | establish less: [M]'s step claims more than the lines (a better constant, a wider range, a dropped hypothesis); the note says what |
| `hasPart` | establish one part of the step's claim(s); the note says which part is not there |
| `relatedMatch` | do this step at this place, but by a different argument or with a different quantity; the note says how |
| `noMatch` | searched for and absent |

Rules:
- Never upgrade a relation beyond the evidence. Compare statements, not names or docstrings.
- **exactMatch vs closeMatch** (fixed after the pilot, where most disagreements were here). These
  are *not* differences, and leave the relation `exactMatch`:
  - renamed variables and symbols (`ϱ` written `s`, the energy as the coordinate `p i`);
  - encodings: `Budget δ` or `∃ C, ∀ᶠ n` for `O(λ^δ)`, a `max` of exponents for a sum of two
    powers, `tsum`/`Finset` sums, casts, bundled structures, the dependence of constants carried
    by quantifier order;
  - a displayed formula proved as a lemma (`bake_test`) where [M] writes it as a definition, or
    the reverse, when the formula is the same;
  - the Lean proof's internal tactics, when the lines establish the step's claim.

  `closeMatch` needs a difference in content that a reader should know: another normalization or
  constant, another interval or range, a hypothesis added or dropped without a clear direction of
  strength, the claim only along a sequence or eventually. Name it in the note.
- **broadMatch** whenever the Lean is mathematically stronger, even mildly (a hypothesis dropped,
  an extra `+1` in a bound, a larger range); **narrowMatch** whenever it is weaker. Use
  `closeMatch` only when there is no direction.
- Before `relatedMatch` or `noMatch` for a display or formula, grep for a `def`/`lemma` of the same
  shape in the files of the item's key declarations (e.g. `grep -n "log.*det" <dir>/*.lean`): [L]
  often has the exact formula under a nickname.
- A step that only sets up (fixes notation, "Use Lemma X", "Let F be ...", "Define") is carried by
  the lines that make the same choice or definition (a `let`, `set`, `obtain`, a `def` used by the
  proof). If the Lean makes the same choice, that is a match; if the Lean has no such object,
  `noMatch`.
- A step that cites a lemma ("by Lemma 12.4, ...") is carried where the Lean proof applies the
  corresponding declaration: link those lines. If the cited item's declaration is stated elsewhere,
  you may add a second end with its statement lines.
- A display that is a definition maps to the `def`'s lines; a display inside a statement maps to the
  lines of the declaration that state that part of the statement (as the first campaign's
  key declarations).
- Prose that asserts nothing mathematical (a reading guide, "We now prove (ii)", a remark that is
  motivation) is `noMatch` with the note "asserts no mathematics" only if no Lean lines correspond
  to it; if the Lean proof is organized the same way (a case split at the same place), link those
  lines.
- When [L]'s proof takes a different route through the same point (another lemma, another
  quantity, an abstract constant where [M] has a number), that is `relatedMatch`, not `noMatch`.
- A number or constant that [M] prints and [L] leaves abstract (`∃ C`, a `Rate` with `o(1)`) is a
  difference: `closeMatch` if [L]'s statement is the same up to it and it does not matter for
  strength, `narrowMatch` if [M]'s explicit value is stronger than what [L] proves.

## Lean ends

Each end is one contiguous range of one declaration:
- `decl`: the fully qualified name, as `stool.py range` prints it (it must resolve exactly);
- `file`: only for a name declared in two files (`stool.py src` prints "also declared at"): the
  file of the declaration you mean, e.g. `Solution.lean` rather than the `sorry` placeholder in
  `Challenge.lean`;
- `lines`: `[first, last]`, inside that declaration's range, as narrow as the fact: the `have`
  line(s) or the statement lines through `:=`, not the whole proof;
- `conclusion`: one sentence saying what fact these lines establish, in mathematical terms with
  the essential Lean name(s) in backticks, e.g. "`levy` splits the additive term into the tail, the
  constant `card (Site c) * f0 0 1`, the masked neighbour sums and the `insight` terms."
- `notation` (optional): rows `{"math": "...", "lean": "..."}` only where the Lean's names need
  them to be read.

Use one end per range; several ends when the step is carried in several places. Put the most
direct one first. [L] often states a result or definition twice, an internal form (`YM.*`) and a
public form (`YangMills.*`, in `Public*.lean`, `ChallengeSpec.lean` and similar): when both carry
the record, give an end for each.

For `noMatch`, the ends name the declarations you checked the step against (the key proof, the
helpers you read), with `lines` their full range or omitted, and no conclusion; `searched` lists
the greps and names you searched.

## Errors in the text

If [M] is wrong here (not just absent from [L]: a false inequality, a wrong constant, a step that
does not follow, a contradiction with what [L] proves), add
`"text_error": {"claim": "...", "evidence": "..."}` saying exactly what is wrong and what [L] has
instead. A typo is `{"claim": "typo: ...", ...}`. Do not report a mere difference of route or an
absence.

## Output

One JSON file, records in the batch's order:

```json
{
  "batch": "P21",
  "agent": "mapper | verifier",
  "records": [
    {
      "id": "Lemma 13.6 step 4",
      "relation": "closeMatch",
      "ends": [
        {"decl": "YM.Fully.Qualified.name", "lines": [120, 123],
         "conclusion": "One sentence."}
      ],
      "note": "One or two sentences, premises first: what differs (required unless exactMatch).",
      "searched": ["for noMatch: greps and names searched"],
      "confidence": "high | medium | low"
    }
  ]
}
```

Notes are one or two sentences, in your own words, premises before conclusions, no hedges. Run
`python3 repo/scripts/steps/stool.py check <file>` and fix every error before you finish.

## Economy

Economy never means a shallower search. Read every key declaration in full and the helpers each
step needs; a `noMatch` needs the key proofs read and at least two greps for the step's own
symbols or constants, listed in `searched`. Save tokens only in how you look: combine lookups
into one shell call (several `stool.py src` or `grep` commands
joined by `;`), read line ranges rather than whole files, and do not reread what you have read.
Write the output file once, when every record is decided (keep the records in your working notes
until then), and fix errors with small edits rather than rewriting the file.
