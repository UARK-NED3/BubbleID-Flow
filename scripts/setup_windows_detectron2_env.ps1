param(
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"

python -m venv $VenvPath
& "$VenvPath\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel

# Install CUDA-enabled PyTorch first. Detectron2 needs torch available while building.
& "$VenvPath\Scripts\python.exe" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Core BubbleID-Flow, annotation, and Detectron2 dependencies with Windows wheels.
& "$VenvPath\Scripts\python.exe" -m pip install `
    "numpy>=1.26,<2.0" `
    scipy `
    pandas `
    matplotlib `
    pillow `
    opencv-python `
    scikit-image `
    pyyaml `
    tqdm `
    labelme `
    pycocotools `
    tensorboard `
    fvcore `
    iopath `
    omegaconf `
    hydra-core `
    cloudpickle `
    tabulate `
    termcolor `
    yacs `
    shapely `
    filterpy

# Build Detectron2 against the already installed PyTorch package.
& "$VenvPath\Scripts\python.exe" -m pip install --no-build-isolation "git+https://github.com/facebookresearch/detectron2.git"

# Install this repo in editable mode.
& "$VenvPath\Scripts\python.exe" -m pip install -e .

& "$VenvPath\Scripts\python.exe" -m pip check
& "$VenvPath\Scripts\python.exe" -c "import torch, detectron2, cv2, labelme, bubbleid_flow; from detectron2 import _C; print('torch', torch.__version__); print('detectron2', detectron2.__version__); print('cuda', torch.cuda.is_available()); print('gpu', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none'); print('cv2', cv2.__version__); print('environment ok')"
