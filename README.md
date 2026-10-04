# english-explain

Executable explanations for English learning: connect input, learner production, feedback, revision, and transfer in one inspectable lesson.

> **Status:** MVP. The public contract and first text-first learner flow are available offline.

The project is not a grammar animation library. It will support aligned text/audio examples, contrastive explanations, dialogue branches, learner attempts, feedback rubrics, and accessible text alternatives.

Initial MVP scenes:

1. sentence structure and meaning;
2. dialogue repair and clarification;
3. pronunciation, stress, and rhythm.

## Learning loop

```text
predict -> understand -> produce -> compare -> revise -> transfer
```

## Lesson bundle contract

`schema/lesson-bundle.schema.json` defines the JSON shape for a learner-facing
lesson. The standard-library validator in `english_explain.schema` adds the
cross-field checks that JSON Schema cannot express here: IDs are unique,
text and optional audio segments share stable IDs, feedback dimensions are
declared by the task, and provenance is explicit. The contract describes an
intended learner level; it does not store a proficiency claim or an overall
score.

Each item follows the same inspectable path:

```text
input -> produce -> feedback -> revise -> transfer
```

Feedback is deterministic and explainable. A dimension declares the terms it
checks, the rationale for the check, and guidance for a revision. There is no
account, network service, speech recognition, personalization, or model-based
scoring in this MVP.

## Run it locally

The runtime has no third-party dependency. From the repository root:

```bash
python -m pip install -e .
english-explain validate fixtures/dialogue-repair.json
english-explain run fixtures/dialogue-repair.json \
  --item clarification-1 \
  --response "Could you repeat that?" \
  --revised-response "Sorry, could you say that again?" \
  --transfer-response "Sorry, could you say the platform number again?"
```

The command prints stable JSON containing the input, response, per-dimension
feedback, revision, and transfer prompt. The same command and inputs produce
the same output, so a learner or teacher can inspect every step.

Run the deterministic test suite with:

```bash
python -m pytest
```

The two fixtures are intentionally original teaching examples. The dialogue
fixture includes a tiny generated local WAV asset only to exercise text/audio
alignment; its text path remains complete and usable without audio.

## Repository boundaries

This repository owns reusable lesson schemas, alignment and playback primitives, and feedback interfaces. Public scenarios live in `boxi-English/english-scenarios`; the site is a separate presentation layer. No learner data or private course records belong here.
