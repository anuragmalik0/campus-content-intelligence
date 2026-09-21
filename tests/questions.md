# Test Questions

Written in Phase 0, before the pipeline exists. Questions written after the
fact tend to be questions the system already answers.

For each: the expected answer, and where in the source material it comes from.

## Single-source — video only

| # | Question | Expected answer | Source |
|---|---|---|---|
| V1 | What physical intuition is given for how Momentum stabilizes optimization across ravines? | Simulating a heavy bowling ball rolling downhill, accumulating velocity in the downhill direction while oscillations across ravine walls cancel out | Lecture 3: Neural Optimization @ 00:01:10 |
| V2 | What causes standard gradient descent to oscillate violently in ravines according to the lecture? | High-dimensional loss landscapes feature ill-conditioned ravines where curvature is much sharper in one direction than another | Lecture 3: Neural Optimization @ 00:00:35 |
| V3 | What problem with standard Adam led to the adoption of AdamW for Transformers? | In standard Adam, L2 regularization interacts incorrectly with adaptive gradient updates; AdamW decouples weight decay directly from gradient updates | Lecture 3: Neural Optimization @ 00:01:50 |

## Single-source — slides / PDF only

| # | Question | Expected answer | Source |
|---|---|---|---|
| D1 | What is the mathematical update rule for gradient descent? | w_{t+1} = w_t - eta * grad(L(w_t)), where negative gradient points in steepest descent direction | Notes, page 1 |
| D2 | Why are saddle points considered a more severe obstacle than local minima in deep networks? | High-dimensional loss surfaces are dominated by saddle points surrounded by flat plateaus | Notes, page 1; Slides, page 2 |
| D3 | What failure mode occurs if the learning rate eta is configured too large? | Optimization diverges, oscillates wildly across steep ravines, and loss explodes to NaN | Notes, page 2; Slides, page 3 |
| D4 | What techniques are described to resolve vanishing and exploding gradients in deep networks? | He/Xavier initialization, residual skip connections, LayerNorm/BatchNorm, and gradient clipping to 1.0 | Notes, page 2 |
| D5 | What is the typical batch size range recommended for mini-batch gradient descent? | 32 to 256 samples | Notes, page 3; Slides, page 4 |
| D6 | What is the physics analogy for Momentum and what is the default gamma parameter value? | A heavy ball rolling down a landscape accumulating velocity; default gamma = 0.9 | Notes, page 4; Slides, page 5 |
| D7 | How does AdamW differ from standard Adam? | Decouples L2 weight decay regularization from gradient updates, fixing a bug in standard Adam | Slides, page 6 |

## Cross-source — needs two or more sources combined

These are the demo. They are also the most sensitive to chunking quality.

| # | Question | Expected answer | Sources |
|---|---|---|---|
| X1 | Compare the memory complexity and GPU hardware trade-offs between Full Batch GD and Mini-batch GD. | Full batch has O(N) memory complexity and fails when data exceeds VRAM; Mini-batch (32-256) maximizes GPU tensor utilization while retaining helpful stochastic regularization noise. | Notes, page 3 & Slides, page 4 |
| X2 | What starting learning rate rules of thumb and scheduling techniques are recommended? | Start with 3e-4 (Karpathy constant) or 1e-3, use linear LR warmup over first 5% of steps, and apply cosine annealing or step decay. | Notes, page 2 & Slides, page 3 |

## Boundary cases

Concepts spanning a chunk boundary, terms mentioned in passing, questions
phrased in vocabulary the lecturer never used.

| # | Question | Why it is hard | Expected behaviour |
|---|---|---|---|
| B1 | What is the Karpathy constant? | Mentioned briefly in passing on the slides | Cites Slides page 3 and identifies 3e-4 starting learning rate for Adam |
| B2 | Can gradient descent get stuck in a bad local minimum when training linear regression? | Requires understanding convex vs non-convex distinction | Explains that linear regression has a convex loss function with a guaranteed global minimum, so it cannot get stuck in bad local minima (Notes, page 1) |

## Out of scope — must be refused

Questions the material does not answer, especially ones the underlying model
definitely knows from general knowledge. If these get answered, grounding has
failed.

| # | Question | Expected behaviour |
|---|---|---|
| O1 | What is the capital city of Australia? | System declines: notes that the course material only covers Gradient Descent and Neural Network Optimization. |
| O2 | How does the scaled dot-product attention formula work in Transformer models? | System declines: states that while Transformers are mentioned in passing regarding AdamW, the attention formula is not covered in this topic. |
| O3 | What is Dijkstra's algorithm and what is its time complexity? | System declines: states that graph shortest-path algorithms are not covered in this material. |
| O4 | How do convolutional neural networks compute 2D kernel convolutions? | System declines: states that 2D convolution operations are outside the scope of this lecture material. |

