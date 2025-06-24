### Ansible + Helm 기반 Kubernetes 자동화 실습 정리

해당 프로젝트는 **도커 기반으로 구성된 Whisper 실시간 음성 분석 시스템** [(WhisperTextAnalyzer GitHub)](https://github.com/ajh9789/WhisperTextAnalyzer)을 바탕으로,  
**Kubernetes 환경에서 Helm Chart, Ingress, 인증서 자동화(cert-manager)** 등 클러스터 운영 흐름을 실습하고,  
**Ansible을 활용한 설치 자동화** 및 **GitHub Actions 기반 Docker 이미지 자동화**를 연습하기 위해 구성되었습니다.

> 본 프로젝트는 단일 노드 기반 Kubernetes 실습이지만,
> **로드밸런서가 없는 환경에서 Ingress + HTTPS 인증 자동화(cert-manager)** 구성 시 구조적인 제약을 겪었습니다.
> http-01 → DNS-01 방식 전환, NodePort 포트 범위 확장 등 다양한 방법을 시도했으나,
> **내부 네트워크 환경에서의 접근 제한 및 DNS 인증 응답 실패**로 인해 인증 자동화에 반복적인 실패가 발생했습니다.

> 또한 본 실습은 초기에는 **WSL2 기반 로컬 환경에서 Minikube와 Helm Chart 설계**로 시작되었고, 이후 **VMware Workstation 기반 로컬 쿠버네티스(kubeadm) 자동화**,
> 그리고 **Azure VM 기반 kubeadm 실습**으로 점진적으로 확장되었습니다.
> 이 과정에서 **네트워크 구성 방식의 차이**, **인증서 발급 오류**, **내부 IP 기반의 접근 한계** 등을 반복적으로 겪으며,
> **실제 인프라 전환 시 고려해야 할 인증 구조와 네트워크 환경의 차이점**을 학습할 수 있었습니다.

> 후속 계획으로 도메인을 구입하고, MetalLB를 통해 LoadBalancer 타입을 구성하여 http-01 인증을 적용하거나, Cloudflare DNS를 연동한 dns-01 인증 방식으로 문제를 해결할 예정입니다.

- FastAPI + Redis + Celery 기반 실시간 분석 시스템
- Whisper 기반 STT 모델 + 감정 분석 모듈 포함
- Docker → Kubernetes → Helm 차트화 → Ansible 자동 설치 → GitHub Actions 자동 빌드 연계
- Let's Encrypt 인증 + TLS Ingress + Grafana 모니터링까지 실습

---

#### 프로젝트 개요

- 주제: WhisperTextAnalyzer 실습 환경을 Kubernetes 상에서 자동화 구성
- 목표: 단일 노드 기반 쿠버네티스 클러스터에서 Helm Chart와 Ansible을 활용한 실습 환경 완성 및 HTTPS 인증까지 구성

#### 주요 도구 및 기술 스택

- Infrastructure: Kubernetes (minikube, kubeadm), Docker, WSL2, VMware, VM(Azure)
- 자동화 도구: Ansible, Helm, GitHub Actions
- 서비스 구성: FastAPI, Redis, Celery, Whisper, Grafana, Prometheus, Loki
- 인증 및 네트워크: Ingress, cert-manager, Let's Encrypt, DuckDNS

#### 프로젝트 디렉토리 구성

- `ansible.cfg`: Ansible 기본 설정 파일 (inventory 위치, 권한 관련 설정 등 포함)
- `inventory/hosts.ini`: 배포 대상 노드 정보 (예: master, worker 노드 등)
- `playbook.yml`: 전체 설치 및 배포 자동화 Playbook
- `roles`: Ansible 역할별 작업 정의

  - `firewall`: 방화벽(UFW) 설정, sysctl 네트워크 세팅
  - `k8s_init`: 쿠버네티스 설치 및 클러스터 초기화 (kubeadm init, kubeconfig 설정 등)
  - `helm_deploy/files/app-chart`: Helm 기반 배포 서비스 차트 구성

    - `Chart.yaml`: Helm 차트 메타 정보
    - `values.yaml`: 전체 서비스 구성 values
    - `grafana-values.yaml`, `loki-values.yaml`: 개별 서비스 values override 파일
    - `templates/*.yaml`: K8s 리소스 템플릿 (Deployment, Service, Ingress, HPA, PVC 등)

#### 자동화 구성 흐름 (firewall → k8s_init → helm_deploy)

1. **네트워크 및 방화벽 초기 설정 (`roles/firewall`)**

   - UFW 방화벽 설치 및 포트 허용 (22, 6443, 80, 443, 30000\~32767 등)
   - `sysctl.conf`에서 bridge-nf-call 설정 적용
   - 모듈 로딩 (`br_netfilter`, `overlay`) 및 네트워크 커널 파라미터 설정
   - iptables 설정과 커널 파라미터 반영 (`sysctl --system`)

2. **쿠버네티스 설치 및 클러스터 초기화 (`roles/k8s_init`)**

   - Docker, containerd, kubeadm, kubelet 설치 및 설정
   - containerd 설정 파일(`/etc/containerd/config.toml`) 생성 및 systemd 활성화
   - `kubeadm init`으로 클러스터 마스터 노드 초기화
   - kubeconfig 파일을 `/home/username/.kube/config`로 복사하여 kubectl 사용 설정
   - Flannel CNI 애드온 적용

3. **Helm Chart 기반 서비스 배포 (`roles/helm_deploy`)**

   - Helm 설치 및 stable/chart repo 등록
   - `app-chart` 디렉토리 기준으로 서비스 배포 구성

     - `values.yaml`: 공통 설정 (서비스 이름, 이미지, 환경 변수 등)
     - 템플릿화된 리소스: Deployment, Service, Ingress, PVC, HPA 포함
   - 주요 구성 요소:

     - FastAPI + Redis 백엔드
     - Celery Worker (STT 처리 및 감정 분석)
     - Grafana, Prometheus, Loki (모니터링)
     - Ingress + cert-manager + TLS 인증 자동화

#### 주요 특징 및 포인트

- 템플릿화된 Helm Chart 사용 → 실습 반복
- ingress.yaml에서 cert-manager.io/cluster-issuer 어노테이션 기반 HTTPS 인증 자동 구성
- secret.yaml, letsencrypt-cert.yaml 등 인증/보안 리소스도 Helm 차트로 통합 관리
- values.yaml 중심의 오버라이딩 구조로 설정 유지

#### 실습 중 겪은 주요 문제와 해결 해야 할 것

- cert-manager CRD 미설치로 인증 실패
- http-01 인증 시 NodePort 포트 제한 이슈 (단일 노드 환경)
- DNS-01 방식 인증 중 DuckDNS hook 오류 발생
- Ingress 경로 충돌, configmap 적용 누락 이슈
- grafana socket 통신 실패 및 경로 인증 오류

---

#### 학습 타임라인 및 회고

 **Week 1 (2025.05.17 \~ 05.24):**

- Kubernetes 기본 구조, minikube 실습을 통한 개념 정리
- FastAPI, Redis, Celery 연동 구조 학습
- NodePort, Dockerfile 구성, 비동기 처리 이해

 **Week 2 (2025.05.25 \~ 06.02):**

- Prometheus, Grafana, Loki 기반 모니터링 구성
- Helm 템플릿 설계 및 배포 흐름 정리
- Ansible로 kubeadm 기반 단일 노드 클러스터 자동화 구성
- VMware 기반 WSL2 연동 및 SSH 설정 처리

 **Week 3 (2025.06.03 \~ 06.14):**

- 인증서 구성(cert-manager, Let's Encrypt), Ingress 연동
- Helm 기반 HTTPS 자동화 구성 및 오류 해결 반복 실습
- DNS 인증 방식 완전 이해 및 sidecar, configmap 충돌 해결
- 단일 노드 구조 회고 및 Azure AKS 전환 가능성 검토

---

#### 실습 기록 디렉토리 구조 요약

> **※ 아래는 날짜별 정리된 디렉토리를 요약한 내용이며, 상세한 실습 내용은 비공개 저장소에 기록되어 있습니다. 상단의 주간별 회고를 함께 참고하면 흐름을 이해하기 쉽습니다. 요약은 상단 주간별 회고 참고.**

```
 2505월
  └─ 250517_k8s: minikube, k8s 개념 정리
  └─ 250518_k8s: 유저 식별, 네트워크 개념
  └─ 250519_k8s: NodePort, Dockerfile, 비동기 구성 실습
  └─ 250520_k8s: 포트포워딩, Docker Hub + GitHub Actions 연동
  └─ 250521_k8s: AudioWorklet, 핵심 쿠버네티스 명령어
  └─ 250522_k8s: STT 중복 단어 필터, 처리 최적화
  └─ 250523_k8s: 클라이언트-서버 최적화
  └─ 250524~250526: Ingress, Prometheus, Grafana 구성 실습
  └─ 250527~250531: 인프라 정리, Helm 개념 및 템플릿 실습 계획


 2506월
  └─ 250601~250602: PVC, HPA, Helm 차트 구조 정리
  └─ 250603~250606: Ansible 자동화, VM 네트워크 구성 및 테스트
  └─ 250607~250609: kubeadm 완성, 인증 흐름 학습
  └─ 250610~250613: 인증서 자동화 및 cert-manager 오류
  └─ 250614: 회고
```
