# 교육 실험 구조

configs/lessons.json → src/generate.py → artifacts/*/values.npz 및 summary.json → figures/*.png → docs/report.md → tools/render_report.mjs → docs/report.pdf → src/check_pdf.py.

| 모듈 | 입력 / 단위 | 출력 계약 | 검증 |
|---|---|---|---|
| frames | 2D 점 m, 회전 무차원 | frames/values.npz: p,R,t,q,wrong,a | 역변환, 순서, norm |
| camera | f px, B m, 깊이 m | camera/values.npz: depth,u,disparity,depth_sigma | 투영 scale, 시차 |
| KITTI | frame120 XYZ m, Tr, P0, grayscale | kitti/values.npz: index,lidar,camera,pixel,indices,pixels | 전방/영상 내부, 실제 overlay |
| estimation | 측정 m, sigma m | estimation/values.npz: 잔차 비용, 공분산, MLE/MAP | 폐형식 정답 비교 |
| linearization | 무차원 scalar, 회전 rad | linearization/values.npz: trace,naive,proper | 유한차분, 직교성 |
| graph | 1D 증분 m, sigma m | graph/values.npz: before,after,J,residual | gauge rank, 끝점 잔차 |
| imu | 초, m/s², deg/s | imu/values.npz: 적분오차, 시간차와 픽셀오차 | 해석식 끝점 |

KITTI에서만 LiDAR→카메라 좌표변환을 수행한다. 시간차 그림은 합성 모델이며 Raw OXTS 시간 정렬을 수행하지 않는다. 픽셀 오차는 가로 등속운동 근사다. 모든 파일은 연구 폴더 아래에 한정되며 기존 파이프라인 접점은 문서 이미지 참조뿐이다.
