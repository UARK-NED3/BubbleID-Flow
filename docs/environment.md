# Environment Setup

This project needs a real instance-segmentation environment for BubbleID-style fine-tuning. The local Windows environment has been tested with:

- Python 3.10.11
- PyTorch 2.5.1 + CUDA 12.1
- torchvision 0.20.1 + CUDA 12.1
- Detectron2 0.6 built from `facebookresearch/detectron2`
- NVIDIA GeForce GTX 1660 SUPER

## Windows Setup

From the repository root:

```powershell
.\scripts\setup_windows_detectron2_env.ps1
```

Then activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Verify:

```powershell
python -c "import torch, detectron2; from detectron2 import _C; print(torch.cuda.is_available())"
```

## Manual Windows Commands

The key detail is that Detectron2 must be installed after PyTorch and with build isolation disabled:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
.\.venv\Scripts\python.exe -m pip install numpy scipy pandas matplotlib pillow opencv-python scikit-image pyyaml tqdm labelme pycocotools tensorboard fvcore iopath omegaconf hydra-core cloudpickle tabulate termcolor yacs shapely filterpy
.\.venv\Scripts\python.exe -m pip install --no-build-isolation "git+https://github.com/facebookresearch/detectron2.git"
.\.venv\Scripts\python.exe -m pip install -e .
```

## Notes

- `super-gradients` is not required for Mask R-CNN segmentation fine-tuning and is not included in the working environment script. It attempted to downgrade core packages during testing.
- The upstream BubbleID package imports `super_gradients` at module import time, but the segmentation training path used here should call Detectron2 directly rather than importing the entire upstream BubbleID module.
- Generated `.venv`, models, datasets, and outputs are ignored by git.
