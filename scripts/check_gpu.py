import torch

print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Device name:", torch.cuda.get_device_name(0))
    print(f"Total VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
    print(f"Allocated: {torch.cuda.memory_allocated(0) / (1024**2):.2f} MB")
    print(f"Reserved: {torch.cuda.memory_reserved(0) / (1024**2):.2f} MB")
