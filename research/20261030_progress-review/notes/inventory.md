# 리소스 인벤토리

2026-10-30 로컬 파일 및 Git 객체 확인. 전체 디스크가 아닌 이 레포의 사용 가능 리소스 범위다.

| 구분 | 확인 결과 | 근거 / 재사용 판단 |
|---|---|---|
| 카메라 | grayscale stereo 00~21, 00 좌우 각각 4,541장 | artifacts/inventory/sequences.json; 우측 영상은 현재 VO에서 미사용 |
| GT | 00~10 pose 텍스트, 11~21 로컬 GT 없음 | 위 JSON; 평가 전용 |
| LiDAR | 00만 4,541개 float32 XYZI bin | data/kitti/dataset/sequences/00/velodyne; 다른 sequence 미추출 |
| IMU/OXTS | Raw 0027, 45,700행 x 30열, 유한값 | artifacts/inventory/imu.json; 영상과 아직 시간 정렬 안 됨 |
| calibration | Odometry P0~P3/Tr, Raw cam-to-cam/imu-to-velo/velo-to-cam | data/kitti/dataset/sequences/00/calib.txt; data/kitti/raw/2011_10_03 |
| timestamps | Odometry 상대 시간, Raw 센서별 절대 시간 | 서로 직접 같은 프레임 번호로 결합 불가 |
| 원본 보관 | archives 아래 Velodyne/Raw extract/calib ZIP 세 개 | 이전 이동 작업 기록: data/kitti/SENSOR_IMPORT.md |
| 현재 feature | ORB 위치, binary descriptor, Hamming distance, 매칭, pose inlier mask | src/vo/features.py:4, :8, :13 |
| 추가 feature | stereo disparity/깊이, LiDAR intensity/normal/plane, IMU 가속도/각속도 | 추출 가능; 실제 알고리즘 입력으로 연결하지 않음 |
| KITTI loader | KittiSequence: K, 왼쪽 영상, GT | src/datasets/kitti.py:7, :26, :32, :42; 확장 필요 |
| two-view | Essential RANSAC 및 recoverPose | src/vo/two_view.py:11; main은 mask 집계 결함 남음 |
| 누적 | 상대 pose 역변환 누적 | src/vo/run_kitti.py:12, :42; metric scale 없음 |
| 시각화 | trajectory plot | src/viz/plot_trajectory.py:7 |
| playback exporter | 이미지/특징점/궤적 HTML 직렬화 | 365baf3:src/viz/export_playback.py:16; main 작업 폴더에 없음 |
| 데이터 도구 | 다운로드/구조 검사/LiDAR BEV | 365baf3:scripts/; main 작업 폴더에 없음 |
| 환경 | Python 3.11.14, OpenCV 5.0.0, NumPy 2.4.6, Matplotlib 3.11.1 | artifacts/provenance/environment.json; requirements는 버전 고정 안 됨 |
| 디버깅 | VSCode launch/settings, offline HTML | 365baf3:.vscode/; 현재 main에는 없음 |
| 보관 결과 | playback.html 200프레임 및 desktop/mobile PNG | outputs/; HTML에 생성 커밋/환경 metadata 없음 |
| 평가 도구 | 이번 회고용 audit.py | 새 VO 추정 없이 보관 결과를 재집계 |
| 없는 것 | stereo VO, triangulation map, BA, loop closure, VIO/LIO, 단위 정렬 평가기 | 관련 구현 없음 |
| 미확인 | 동적 객체별 GT, 날씨/고속/회전 조건별 분포, latency, 센서 noise/bias | 이번 inventory에서 확인 안 됨 |

CRC 검증은 앞선 추출 실행 기록에 근거하며 이번에는 100GB 이상 원본 전체를 다시 읽지 않았다.
모든 LiDAR 파일의 의미적 유효성/센서 결함까지 검증했다고 해석하지 않는다.
