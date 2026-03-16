import inspect
from dashscope.audio.asr import Recognition, RecognitionCallback

# Check Recognition __init__ signature
print("Recognition.__init__ signature:")
print(inspect.signature(Recognition.__init__))
print()

# Check if callback is required
sig = inspect.signature(Recognition.__init__)
for param_name, param in sig.parameters.items():
    if param_name != 'self':
        print(f"Parameter: {param_name}")
        print(f"  - Default: {param.default}")
        print(f"  - Kind: {param.kind}")
        print()