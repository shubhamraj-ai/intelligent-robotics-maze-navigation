# Step 5 final simple perceptron

The selected model is a single 3-class linear softmax layer: 50x50 camera JPEG -> OpenCV grayscale -> float32 /255 -> flatten 2500 -> forward/left/right. This simple coursework-aligned architecture needs no hidden layers or CNN components.

The earlier learning rate 0.08 / 400 epochs was seed-sensitive. Learning rate 0.01 / 3200 epochs converged reproducibly across seeds 1?5. The preferred unweighted runs achieved pooled accuracy 0.9221?0.9247, macro-F1 0.8218?0.8295, forward recall 0.9840, left recall 0.7222?0.7500 and right recall 0.5833?0.6111. Forward-to-turn false positives were 1.60%.

Full balancing raised left/right recall to 0.9444/0.9722, but reduced forward recall to 0.8626 and increased forward-to-turn false positives to 13.74% (accuracy 0.8805, macro-F1 0.8072). This materially increases premature-turn risk. Balanced weighting remains an experimental fallback pending live Step-6 behavior; it is not the selected submission configuration. These selection results are prior experimental evidence, not a new live-control evaluation.

Final configuration: epochs=3200, learning_rate=0.01, l2=0.0001, seed=42, class_weighting=none. Validation is leave-one-session-out over three sessions using 385 official fresh images (313 forward, 36 left, 36 right). CV retains the existing fold seeds base+1 through base+3; final training now uses seed 42 without an offset. CLI overrides, including --class-weighting balanced, remain available.

Use notebooks/step05_final_simple_perceptron_colab.ipynb in Colab. Set the Drive ZIP and output paths. The official ZIP has top-level forward/, left/, right/ folders and session-prefixed filenames such as session_20261103_01__forward_000001.jpg. The notebook verifies counts and dimensions, runs CV, trains the NumPy model, transfers weights to Keras, checks prediction parity, and exports the trained .h5 and JSON evidence. TensorFlow is needed only in Colab for export.

Official Step-5 deliverables are the completed Colab .ipynb and trained .h5. The JSON records configuration, metrics, software versions and the ZIP checksum. The local NumPy trainer uses generic output names under models/step05_simple_perceptron; existing historical balanced artifacts remain untouched. Use separate --output-dir values when comparing experiments.

Step 6 is explicitly NOT completed by this change. No autonomous controller, scene changes, dataset collection or Step 7 work is included.
