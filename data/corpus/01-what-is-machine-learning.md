# What Is Machine Learning?

Machine learning (ML) is a subfield of artificial intelligence in which a computer
system learns to perform a task by finding patterns in data, rather than by following
hand-written rules. Instead of a programmer specifying every decision the system should
make, the programmer chooses a model family and a training procedure, then feeds the
system examples. The system adjusts its internal parameters until its outputs match the
examples as closely as possible.

## The three main learning paradigms

**Supervised learning** is the most common paradigm. Every training example carries a
label — the correct answer. A spam filter trained on emails tagged "spam" or "not spam"
is a classic example. The model learns to map inputs to labels.

**Unsupervised learning** uses unlabelled data. The model searches for structure on its
own: clusters of similar items, compressed representations, or the probability
distribution of the data itself. Dimensionality reduction and generative models live
here.

**Reinforcement learning** trains an agent by rewarding it for good actions and
penalising bad ones. Rather than a fixed dataset, the agent interacts with an
environment — a game, a robot simulator, or a real system — and improves through
trial and error.

## Why it works

ML models are universal function approximators: given enough parameters and data, they
can learn arbitrarily complex input-to-output mappings. The training loop minimises a
*loss function* — a number that measures how wrong the model's current predictions are.
Gradient descent, or one of its variants, updates the parameters in the direction that
reduces the loss.

The key risk is **overfitting**: learning the training data so precisely that the model
fails on new inputs. Regularisation techniques, dropout, and holding out a validation
set all guard against this.
