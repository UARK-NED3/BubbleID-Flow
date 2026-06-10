# Lightweight Annotation-Driven Segmentation

This workflow uses student Labelme annotations to train a simple bubble/background pixel classifier. It is designed to run on machines without PyTorch or Detectron2.

## Inputs

- Labelme `.json` files paired with the original `.bmp` images.
- One foreground class is used internally: `bubble`.
- The labels `bubble` and `bubble_cluster` are both mapped to foreground.

## Current Training Command

```powershell
$env:PYTHONPATH="src"

python scripts/train_pixel_model.py `
  --annotation-root "C:\Users\hanhu\Box\NED3_Share\0_BubbleID\BubbleID-Flow\Abrar Hoq Fahim" `
  --annotation-root "C:\Users\hanhu\Box\NED3_Share\Zulkar Nain Prince\Annotation (Flow Boiling)" `
  --model-out "models\pixel_gaussian_flow_roi490_60.json" `
  --report-out "outputs\evaluation\pixel_gaussian_flow_roi490_60.csv" `
  --examples-out "outputs\evaluation\pixel_gaussian_examples_roi490_60" `
  --roi 0,490,1024,60 `
  --threshold 0.45 `
  --min-area-px 20
```

## Current Validation Result

Using every fifth annotated image as a holdout set:

- training images: 57
- validation images: 15
- validation mean IoU: about 0.44
- validation median IoU: about 0.49

This is enough for a useful first-pass overlay, but it is below the quality expected from a fine-tuned instance segmentation model.

## Known Limitations

- The model segments a near-wall ROI rather than the full 1024 x 1024 frame.
- It is a semantic foreground mask, not instance-separated bubbles.
- It still confuses some bubble edges with wall/reflection texture.
- It cannot learn high-level bubble shape context the way Mask R-CNN can.

## Next Upgrade

The next major improvement should be a Detectron2 Mask R-CNN fine-tune using the same Labelme annotations converted to COCO instance segmentation format.
