# BioArtlas Web

BioArtlas 프로젝트의 웹 프론트엔드입니다.

## 프로젝트 정보

BioArtlas는 81개의 바이오아트 작품을 13개의 분석 차원에서 분석하는 계산적 프레임워크입니다.

## 기술 스택

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## 개발 환경 설정

Node.js & npm이 설치되어 있어야 합니다 - [nvm으로 설치하기](https://github.com/nvm-sh/nvm#installing-and-updating)

```sh
# 의존성 설치
npm install

# 개발 서버 시작
npm run dev
```

## 빌드

```sh
npm run build
```

## 프로젝트 구조

```
src/
├── components/    # React 컴포넌트
├── hooks/         # 커스텀 훅
├── lib/           # 유틸리티 함수
├── pages/         # 페이지 컴포넌트
└── assets/        # 정적 파일
```
