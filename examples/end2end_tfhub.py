"""
This example retrieves a model from tensorflowhub.
It is converted into ONNX. Predictions are compared to
the predictions from tensorflow to check there is no
discrepencies. Inferencing time is also compared between
*onnxruntime*, *tensorflow* and *tensorflow.lite*.
"""
from onnxruntime import InferenceSession
import os
import sys
import subprocess
import timeit
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import Input
try:
    import tensorflow_hub as tfhub
except ImportError:
    # no tensorflow_hub
    print("tensorflow_hub not installed.")
    sys.exit(0)

########################################
# Downloads the model.
hub_layer = tfhub.KerasLayer(
    "https://tfhub.dev/google/efficientnet/b0/classification/1")
model = keras.Sequential()
model.add(Input(shape=(224, 224, 3), dtype=tf.float32))
model.add(hub_layer)
print(model.summary())

########################################
# Saves the model.
if not os.path.exists("efficientnetb0clas"):
    os.mkdir("efficientnetb0clas")
tf.keras.models.save_model(model, "efficientnetb0clas")

input_names = [n.name for n in model.inputs]
output_names = [n.name for n in model.outputs]
print('inputs:', input_names)
print('outputs:', output_names)

########################################
# Testing the model.
input = np.random.randn(2, 224, 224, 3).astype(np.float32)
expected = model.predict(input)
print(expected)

########################################
# Run the command line.
proc = subprocess.run(
    'python -m tf2onnx.convert --saved-model efficientnetb0clas '
    '--output efficientnetb0clas.onnx --opset 12'.split(),
    capture_output=True)
print(proc.returncode)
print(proc.stdout.decode('ascii'))
print(proc.stderr.decode('ascii'))

########################################
# Runs onnxruntime.
session = InferenceSession("efficientnetb0clas.onnx")
got = session.run(None, {'input_1:0': input})
print(got[0])

########################################
# Measures the differences.
print(np.abs(got[0] - expected).max())

########################################
# Measures processing time.
print('tf:', timeit.timeit('model.predict(input)',
                           number=10, globals=globals()))
print('ort:', timeit.timeit("session.run(None, {'input_1:0': input})",
                            number=10, globals=globals()))

########################################
# Freezes the graph with tensorflow.lite.
converter = tf.lite.TFLiteConverter.from_saved_model("efficientnetb0clas")
tflite_model = converter.convert()
with open("efficientnetb0clas.tflite", "wb") as f:
    f.write(tflite_model)

# Builds an interpreter.
interpreter = tf.lite.Interpreter(model_path='efficientnetb0clas.tflite')
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
print("input_details", input_details)
print("output_details", output_details)
index = input_details[0]['index']


def tflite_predict(input, interpreter=interpreter, index=index):
    res = []
    for i in range(input.shape[0]):
        interpreter.set_tensor(index, input[i:i + 1])
        interpreter.invoke()
        res.append(interpreter.get_tensor(output_details[0]['index']))
    return np.vstack(res)


print(input[0:1].shape, "----", input_details[0]['shape'])
output_data = tflite_predict(input, interpreter, index)
print(output_data)

########################################
# Measures processing time again.

print('tf:', timeit.timeit('model.predict(input)',
                           number=10, globals=globals()))
print('ort:', timeit.timeit("session.run(None, {'input_1:0': input})",
                            number=10, globals=globals()))
print('tflite:', timeit.timeit('tflite_predict(input)',
                               number=10, globals=globals()))
