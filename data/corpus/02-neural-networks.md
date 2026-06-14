# Neural Networks

A neural network is a machine learning model loosely inspired by the structure of
biological brains. It is organised into **layers** of computational units called
neurons. Each neuron computes a weighted sum of its inputs, adds a bias term, then
passes the result through a non-linear **activation function** such as ReLU or sigmoid.
Stacking many layers lets the network build increasingly abstract representations of
its input.

## Architecture basics

The first layer is the **input layer** — one node per raw feature (e.g., one pixel
value per pixel in an image). Hidden layers in the middle extract features. The
**output layer** produces the prediction: a single number for regression, or a
probability distribution over classes for classification (using a softmax activation).

A fully-connected, or **dense**, layer connects every neuron to every neuron in the
previous layer. Specialised architectures restrict this connectivity for efficiency and
inductive bias:

- **Convolutional neural networks (CNNs)** share weights across spatial positions,
  making them efficient for image and audio data.
- **Recurrent neural networks (RNNs)** pass a hidden state from one time step to the
  next, handling sequential data.
- **Transformers** use attention mechanisms (no recurrence) and have become the
  dominant architecture for language, vision, and multi-modal tasks.

## Training

Training adjusts the network's weights to minimise a loss function. The workhorse
algorithm is **backpropagation**: the chain rule of calculus is applied layer by layer
to compute the gradient of the loss with respect to every weight. An optimiser — most
commonly **Adam** or **SGD with momentum** — then nudges each weight in the direction
that reduces the loss.

Modern networks can have billions of parameters. Training them requires GPUs or TPUs,
large datasets, and careful hyperparameter tuning (learning rate, batch size, weight
decay).
