from __future__ import annotations

import argparse
import os
from pathlib import Path

import torch
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog
from detectron2.data.datasets import register_coco_instances
from detectron2.engine import DefaultTrainer
from detectron2.evaluation import COCOEvaluator


class BubbleTrainer(DefaultTrainer):
    @classmethod
    def build_evaluator(cls, cfg, dataset_name, output_folder=None):
        if output_folder is None:
            output_folder = os.path.join(cfg.OUTPUT_DIR, "eval")
        return COCOEvaluator(dataset_name, output_dir=output_folder)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune Detectron2 Mask R-CNN for flow bubbles.")
    parser.add_argument("--train-json", required=True)
    parser.add_argument("--val-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-iter", type=int, default=600)
    parser.add_argument("--eval-period", type=int, default=100)
    parser.add_argument("--base-lr", type=float, default=2.5e-4)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    train_name = "bubbleid_flow_train"
    val_name = "bubbleid_flow_val"
    register_coco_instances(train_name, {}, args.train_json, "")
    register_coco_instances(val_name, {}, args.val_json, "")
    MetadataCatalog.get(train_name).thing_classes = ["bubble"]
    MetadataCatalog.get(val_name).thing_classes = ["bubble"]

    cfg = get_cfg()
    cfg.merge_from_file(
        model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
    )
    cfg.DATASETS.TRAIN = (train_name,)
    cfg.DATASETS.TEST = (val_name,)
    cfg.DATALOADER.NUM_WORKERS = 0
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(
        "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
    )
    cfg.MODEL.DEVICE = args.device
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 128
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
    cfg.MODEL.ANCHOR_GENERATOR.SIZES = [[8], [16], [32], [64], [128]]
    cfg.SOLVER.IMS_PER_BATCH = args.batch_size
    cfg.SOLVER.BASE_LR = args.base_lr
    cfg.SOLVER.MAX_ITER = args.max_iter
    cfg.SOLVER.STEPS = []
    cfg.TEST.EVAL_PERIOD = args.eval_period
    cfg.INPUT.MIN_SIZE_TRAIN = (512, 640)
    cfg.INPUT.MAX_SIZE_TRAIN = 900
    cfg.INPUT.MIN_SIZE_TEST = 640
    cfg.INPUT.MAX_SIZE_TEST = 900
    cfg.OUTPUT_DIR = args.output_dir

    output_dir = Path(cfg.OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "config.yaml").write_text(cfg.dump(), encoding="utf-8")

    trainer = BubbleTrainer(cfg)
    trainer.resume_or_load(resume=False)
    trainer.train()


if __name__ == "__main__":
    main()
