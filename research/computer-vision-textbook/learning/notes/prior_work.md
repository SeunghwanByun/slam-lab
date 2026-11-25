# 학습과 시각 표현의 원문 근거

## 최적화와 확률
### Takeaway
손실 최소화와 확률 신뢰도는 다른 계약이다.
### Cited Findings
- Kingma, Ba, Adam: A Method for Stochastic Optimization, ICLR 2015 (preprint 2014), 모멘트 기반 갱신: https://arxiv.org/abs/1412.6980
- Ioffe, Szegedy, Batch Normalization: Accelerating Deep Network Training by Reducing Internal Covariate Shift, 2015: https://arxiv.org/abs/1502.03167
- Srivastava, Hinton, Krizhevsky, Sutskever, Salakhutdinov, Dropout: A Simple Way to Prevent Neural Networks from Overfitting, JMLR 2014: https://jmlr.org/papers/v15/srivastava14a.html
- Guo, Pleiss, Sun, Weinberger, On Calibration of Modern Neural Networks, ICML 2017: https://proceedings.mlr.press/v70/guo17a.html
### Inferences
교육용 합성 표본으로 gradient 및 calibration의 차이를 검증할 수 있다.
### Gaps
실제 배포 분포의 calibration 보장은 미검증.

## 공간 표현과 출력 평가
### Takeaway
네트워크 구조보다 출력 좌표와 평가 규약을 먼저 고정한다.
### Cited Findings
- He, Zhang, Ren, Sun, Deep Residual Learning for Image Recognition, CVPR 2016/preprint 2015: https://arxiv.org/abs/1512.03385
- Ronneberger, Fischer, Brox, U-Net: Convolutional Networks for Biomedical Image Segmentation, MICCAI 2015: https://arxiv.org/abs/1505.04597
- Lin, Dollar, Girshick, He, Hariharan, Belongie, Feature Pyramid Networks for Object Detection, CVPR 2017/preprint 2016: https://arxiv.org/abs/1612.03144
- Girshick, Donahue, Darrell, Malik, Rich feature hierarchies for accurate object detection and semantic segmentation, CVPR 2014/preprint 2013: https://arxiv.org/abs/1311.2524
- Ren, He, Girshick, Sun, Faster R-CNN: Towards Real-Time Object Detection with Region Proposal Networks, 2015: https://arxiv.org/abs/1506.01497
- Redmon, Divvala, Girshick, Farhadi, You Only Look Once: Unified, Real-Time Object Detection, CVPR 2016/preprint 2015: https://arxiv.org/abs/1506.02640
- Lin, Goyal, Girshick, He, Dollar, Focal Loss for Dense Object Detection, ICCV 2017: https://arxiv.org/abs/1708.02002
- Carion, Massa, Synnaeve, Usunier, Kirillov, Zagoruyko, End-to-End Object Detection with Transformers, ECCV 2020: https://arxiv.org/abs/2005.12872
### Inferences
고정 필터와 합성 박스는 계산 계약 검증에 즉시 적용. 실제 검출기 설치는 별도.
### Gaps
VOC PDF는 웹 502였으나 공식 VOC2010 HTML에서 all-data-points AP 변경을 확인했다: https://www.robots.ox.ac.uk/~vgg/projects/pascal/VOC/voc2010/index.html . COCO 공식 evaluator의 IoU/recall/area/maxDets 규약을 직접 확인했다: https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py . KITTI 검출 GT 없음.

## 토큰과 기하학
### Takeaway
표현의 유사도와 물리적 깊이/위치는 별개다.
### Cited Findings
- Vaswani 외 8인, Attention Is All You Need, NeurIPS 2017: https://arxiv.org/abs/1706.03762
- Dosovitskiy 외, An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale, ICLR 2021/preprint 2020: https://arxiv.org/abs/2010.11929
- Chen, Kornblith, Norouzi, Hinton, A Simple Framework for Contrastive Learning of Visual Representations, ICML 2020: https://arxiv.org/abs/2002.05709
- Radford 외, Learning Transferable Visual Models From Natural Language Supervision, ICML 2021: https://arxiv.org/abs/2103.00020
- He, Chen, Xie, Li, Dollar, Girshick, Masked Autoencoders Are Scalable Vision Learners, CVPR 2022/preprint 2021: https://arxiv.org/abs/2111.06377
- Kirillov 외, Segment Anything, ICCV 2023: https://arxiv.org/abs/2304.02643
- Ranftl, Lasinger, Hafner, Schindler, Koltun, Towards Robust Monocular Depth Estimation: Mixing Datasets for Zero-shot Cross-dataset Transfer, preprint 2019, TPAMI 2022: https://arxiv.org/abs/1907.01341
- Ranftl, Bochkovskiy, Koltun, Vision Transformers for Dense Prediction, ICCV 2021: https://arxiv.org/abs/2103.13413
- Teed, Deng, RAFT: Recurrent All-Pairs Field Transforms for Optical Flow, ECCV 2020: https://arxiv.org/abs/2003.12039
- Teed, Deng, DROID-SLAM: Deep Visual SLAM for Monocular, Stereo, and RGB-D Cameras, NeurIPS 2021: https://arxiv.org/abs/2108.10869
- Han, Mao, Dally, Deep Compression: Compressing Deep Neural Networks with Pruning, Trained Quantization and Huffman Coding, ICLR 2016/preprint 2015: https://arxiv.org/abs/1510.00149
- Jacob, Kligys, Chen, Zhu, Tang, Howard, Adam, Kalenichenko, Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference, CVPR 2018/preprint 2017: https://arxiv.org/abs/1712.05877
- Hinton, Vinyals, Dean, Distilling the Knowledge in a Neural Network, preprint 2015 (원문 comments는 NIPS 2014 workshop): https://arxiv.org/abs/1503.02531
- He, Gkioxari, Dollar, Girshick, Mask R-CNN, ICCV 2017: https://arxiv.org/abs/1703.06870
- Kirillov, He, Girshick, Rother, Dollar, Panoptic Segmentation, CVPR 2019/preprint 2018: https://arxiv.org/abs/1801.00868
### Inferences
NumPy attention과 합성 깊이 affine 정렬로 인터페이스 오해를 검증할 수 있다.
### Gaps
모든 pretrained 성능 재현은 범위 밖. SAM/CLIP/DPT/RAFT/DROID 미실행.

| 후보 | 필요 입력 | 보유 | 적용 판단 |
|---|---|---|---|
| NumPy toy 학습 | 합성 x,y | 생성 | 즉시 적용, 생산 대체 아님 |
| OpenCV 필터 | grayscale | 있음 | 즉시 적용, 학습 feature 아님 |
| SciPy Hungarian | 비용 행렬 | 합성 | 즉시 적용 |
| 실제 foundation model | 가중치/환경/GT | 없음 | 이 작업 불가, 설명만 |
