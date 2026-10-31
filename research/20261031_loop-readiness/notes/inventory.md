# 문제 정의와 리소스

요청: SLAM/loop closure 연구용 재방문 데이터가 있는지 확인하고 기존 VO/LO 비교 재생 및 기능별 Git 기록을 제공한다.
성공 기준: 전체00 GT에서 시간적으로 떨어진 근접 위치쌍을 찾고 실제 영상으로 확인; 후보 인덱스/거리/상대 시선각/규칙을 저장; 자동 검출 결과와 구분.
입력: poses/00.txt, times.txt, image_0; 이미 보유한 4541프레임. LO 비교는 기존 200프레임 연구 결과를 사용한다.
출력: 후보 CSV/JSON, 전체 경로 그림, 후보 영상쌍, 브라우저 viewer, report.pdf.
[가정] 5m/500프레임/100m 이동/시선30도 이내는 교육용 후보 선택 기준이다. GT 위치는 센서가 관측한 실제 장소 일치를 완전히 보증하지 않는다.
범위 밖: 실제 descriptor-based place recognition, ICP loop 검증, pose graph 최적화, 전체4541프레임 odometry 재실행.

## Quick-win

추정 알고리즘 추가가 아니라 데이터 가용성 확인이므로 GT 근접 검색으로 충분하다. SciPy cKDTree와 기존 영상 loader 형식을 재사용한다.
새 SLAM 논문 구현이나 대규모 선행연구는 수행하지 않는다. 이는 loop closure 알고리즘 성능 실험이 아니다.
