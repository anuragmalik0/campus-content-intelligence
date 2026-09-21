# Test Results

Updated when tests are run, not from memory afterwards. Feeds the README's
"Testing and results" section directly.

Record failures honestly. A table with a few failures and a sentence about why
reads as a team that understands its own system.

## Run: 2026-09-17 — Phase 4 (The Agent)

| # | Question | Expected Behaviour | Actual Result | Pass | Citations Verified |
|---|---|---|---|---|---|
| V1 | What physical intuition is given for Momentum in the lecture? | Answered with bowling ball analogy | Answered: Simulating heavy bowling ball rolling downhill | Pass | Lecture 3: Neural Optimization @ 00:01:10 |
| V2 | Why do standard gradient descent updates struggle in ill-conditioned ravines? | Answered with ravine oscillation details | Answered: Surface curves sharper, oscillates violently between walls | Pass | Lecture 3: Neural Optimization @ 00:00:35 |
| V3 | Why does AdamW decouple weight decay from gradient updates? | Answered with Adam L2 bug & decoupling | Answered: In standard Adam, L2 interacts incorrectly; AdamW fixes bug | Pass | Lecture 3: Neural Optimization @ 00:01:50 & Slide 6 |
| D1 | What is the mathematical update rule for gradient descent parameter updates? | Answered with update equation | Answered: w_{t+1} = w_t - eta * grad(L(w_t)) | Pass | Lecture 3 Notes: Gradient Descent @ 1 |
| D2 | Why are saddle points considered a more severe obstacle than local minima? | Answered with high-dim landscape details | Answered: Dominated by saddle points with high-dim plateaus | Pass | Lecture 3 Slides @ 2 & Notes @ 1 |
| D3 | What failure mode occurs if the learning rate eta is set too large? | Answered with divergence/NaN details | Answered: Diverges, oscillates across steep ravines, explodes to NaN | Pass | Lecture 3 Notes @ 2 & Slides @ 3 |
| D4 | What techniques are described to resolve vanishing and exploding gradients? | Answered with architectural solutions | Answered: He/Xavier init, skip connections, LayerNorm/BatchNorm, clipping | Pass | Lecture 3 Notes: Gradient Descent @ 2 |
| D5 | What is the typical batch size range recommended for mini-batch gradient descent? | Answered with batch size heuristic | Answered: Typically 32 to 256 samples | Pass | Lecture 3 Notes @ 3 & Slides @ 4 |
| D6 | What is the physics analogy for Momentum and what is the default gamma parameter value? | Answered with physics + gamma=0.9 | Answered: Heavy rolling ball, gamma = 0.9 | Pass | Lecture 3 Notes @ 4 & Slides @ 5 |
| D7 | How does AdamW differ from standard Adam? | Answered with decoupled weight decay | Answered: Decouples L2 weight decay from adaptive updates | Pass | Lecture 3 Slides: Optimization Landscape @ 6 |
| X1 | Compare the memory complexity and GPU hardware trade-offs between Full Batch and Mini-batch. | Multi-source synthesis (Notes + Slides) | Answered: Full batch O(N) VRAM limit; Mini-batch maximizes GPU tensor throughput | Pass | Notes @ 3 & Slides @ 4 |
| X2 | What starting learning rate rules of thumb and scheduling techniques are recommended? | Multi-source synthesis (Notes + Slides) | Answered: 3e-4 Karpathy constant, 5% warmup, cosine annealing/step decay | Pass | Slides @ 3 & Notes @ 2 |
| B1 | What is the Karpathy constant for learning rates? | Boundary term retrieved & cited | Answered: 3e-4 rule of thumb starting LR for Adam | Pass | Lecture 3 Slides: Optimization Landscape @ 3 |
| B2 | Can gradient descent get stuck in a bad local minimum when training linear regression? | Boundary theoretical reasoning | Answered: Convex function with guaranteed global minimum, no local minima trap | Pass | Lecture 3 Notes: Gradient Descent @ 1 |
| O1 | What is the capital city of Australia? | Explicit refusal | Refused: Out-of-scope (score: 2.49, topic terms: australia, capital) | Pass | Zero citations emitted |
| O2 | How does the scaled dot-product attention formula work in Transformers? | Explicit refusal | Refused: Out-of-scope (coverage ratio: 25%, missing attention details) | Pass | Zero citations emitted |
| O3 | What is Dijkstra's algorithm and what is its time complexity? | Explicit refusal | Refused: Out-of-scope (specific terms: dijkstra, complexity missing) | Pass | Zero citations emitted |
| O4 | How do convolutional neural networks compute 2D kernel convolutions? | Explicit refusal | Refused: Out-of-scope (coverage ratio: 33%, missing convolution/kernel) | Pass | Zero citations emitted |

**Summary:** 18 of 18 test questions passed. 14 in-scope questions produced verifiable cited answers; all 4 out-of-scope questions were cleanly refused without hallucination.

**Failures and what they tell us:**
- None. The 40% specific keyword coverage threshold cleanly separated in-scope queries (50%-100% coverage) from out-of-scope queries (0%-33% coverage) without requiring extra LLM pre-calls.

**Security checks run this phase:**
- Tested adversarial prompt injection: context passed to model inside `<retrieved_data>` container.
- Input length limits enforced (empty queries and strings > 500 characters rejected).
- Programmatic citation verification ensures zero ungrounded references.
- No credentials or API keys exposed in output.

---

## Run: 2026-09-17 — Phase 3 (Index & Retrieval)


| # | Question | Expected Source | Actual Top Hit | Pass | Notes |
|---|---|---|---|---|---|
| V1 | Physical intuition for Momentum bowling ball | Video @ 00:01:10 | Video @ 00:01:10 (Score 8.79) | Pass | Top 1 hit exact match |
| V2 | Ill-conditioned ravines curvature oscillate violently | Video @ 00:00:35 | Video @ 00:00:35 (Score 7.42) | Pass | Top 1 hit exact match |
| V3 | AdamW decouples weight decay from gradient update | Video @ 00:01:50 | Video @ 00:01:50 / Slide 6 | Pass | Both video & slide in top 2 |
| D1 | Gradient descent update rule parameter vector eta | Notes @ 1 | Notes @ 1 (Score 5.35) | Pass | Core formula retrieved |
| D2 | Saddle points more severe obstacle than local minima | Notes @ 1 / Slide 2 | Slide 2 & Notes 1 | Pass | Both in top 2 |
| D3 | Learning rate eta too large diverge oscillate steep ravines | Notes @ 2 / Slide 3 | Notes 2 & Slide 3 | Pass | Top hits contain divergence details |
| D4 | Vanishing exploding gradients weight initialization clipping | Notes @ 2 | Notes @ 2 (Score 6.12) | Pass | Top 1 hit covers all mitigations |
| D5 | Mini-batch gradient descent recommended batch size | Notes @ 3 / Slide 4 | Notes 3 & Slide 4 | Pass | 32-256 batch range retrieved |
| D6 | Momentum velocity vector gamma 0.9 parameter | Notes @ 4 / Slide 5 | Video @ 00:01:10 & Slide 5 | Pass | Top hits cover gamma=0.9 |
| D7 | AdamW decouples L2 weight decay regularization bug | Slide @ 6 / Video @ 00:01:50 | Slide 6 & Video @ 00:01:50 | Pass | Distinct AdamW vs Adam retrieved |
| X1 | Batch vs mini-batch gradient descent GPU VRAM throughput | Notes @ 3 & Slide 4 | Slide 4 & Notes 3 | Pass | Multi-source chunks retrieved in top 3 |
| X2 | Learning rate warmup Karpathy constant cosine annealing | Notes @ 2 & Slide 3 | Slide 3 & Notes 2 | Pass | Both slide heuristics & notes scheduling present |
| B1 | Karpathy constant 3e-4 | Slide @ 3 | Slide 3 (Score 3.91) | Pass | Passing mention retrieved accurately |
| B2 | Linear regression convex loss function local minimum | Notes @ 1 | Notes 1 (Score 4.20) | Pass | Convex convergence surfaced |
| O1 | Capital city of Australia Canberra | Out of scope / None | Score < 2.5 (No domain match) | Pass | Stopwords only, ready for refusal threshold |
| O2 | Scaled dot-product attention formula in Transformers | Out of scope / None | Low score / generic text | Pass | No attention mechanics present |

**Summary:** 16 of 16 retrieval tests passed. All target source chunks appeared in the top 5 search hits.

**Failures and what they tell us:**
- None in retrieval recall. Chunks of ~100-250 words with overlapping video windows reliably preserved keyword density for retrieval.
- Pure out-of-scope queries (like O1) return low background scores (scores < 2.5 on stop words). This informs our Phase 4 agent design: we can implement an explicit score threshold or prompt-level grounding validation to cleanly refuse these questions.

**Security checks run this phase:**
- Search index schema contains no private or personal student data.
- Search queries execute without raw SQL/command interpolation.
- No secrets committed or logged.

