# english-explain

Executable explanations for English learning: connect input, learner production, feedback, revision, and transfer in one inspectable lesson.

> **Status:** scaffold. The public contract and first MVP are being designed.

The project is not a grammar animation library. It will support aligned text/audio examples, contrastive explanations, dialogue branches, learner attempts, feedback rubrics, and accessible text alternatives.

Initial MVP scenes:

1. sentence structure and meaning;
2. dialogue repair and clarification;
3. pronunciation, stress, and rhythm.

## Learning loop

```text
predict -> understand -> produce -> compare -> revise -> transfer
```

## Repository boundaries

This repository owns reusable lesson schemas, alignment and playback primitives, and feedback interfaces. Public scenarios live in `boxi-English/english-scenarios`; the site is a separate presentation layer. No learner data or private course records belong here.
