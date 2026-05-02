<template>
  <v-app :theme="'dark'">
    <!-- 모바일 전용 메시지 오버레이 -->
    <div 
      v-if="isMobile" 
      class="mobile-overlay"
    >
      <div class="mobile-message-container">
        <div class="mobile-message-content">
          <!-- 아이콘 -->
          <div class="mobile-icon-container mb-6">
            <v-icon size="120" color="grey-lighten-1" class="mb-4">
              mdi-monitor
            </v-icon>
            <v-icon size="80" color="primary" class="mobile-arrow">
              mdi-arrow-left
            </v-icon>
          </div>
          
          <!-- 메인 메시지 -->
          <h1 class="mobile-title text-h4 text-white font-weight-bold mb-4 text-center">
            BioArtlas
          </h1>
          
          <h2 class="mobile-subtitle text-h6 text-grey-lighten-1 mb-6 text-center" v-html="$t('mobile.subtitle')">
          </h2>

          <!-- 임시 디버깅 정보 -->
          <div class="debug-info text-caption text-grey-lighten-2 mb-4 pa-3" style="background: rgba(255,255,255,0.1); border-radius: 8px;">
            <div><strong>{{ $t('mobile.debugInfo') }}:</strong></div>
            <div>{{ $t('mobile.screenWidth') }}: {{ debugInfo.width }}px</div>
            <div>{{ $t('mobile.screenHeight') }}: {{ debugInfo.height }}px</div>
            <div>{{ $t('mobile.mobileDetected') }}: {{ isMobile }}</div>
            <div>Vuetify smAndDown: {{ $vuetify.display.smAndDown }}</div>
            <div>Vuetify mdAndUp: {{ $vuetify.display.mdAndUp }}</div>
            <div>User Agent: {{ debugInfo.userAgent }}</div>
          </div>
          
          <!-- 설명 -->
          <div class="mobile-description text-center mb-8">
            <v-chip 
              v-for="feature in mobileFeatures" 
              :key="feature"
              size="small" 
              color="grey-darken-2" 
              class="ma-1"
            >
              <v-icon start size="small">mdi-check</v-icon>
              {{ $t(`mobile.features.${feature}`) }}
            </v-chip>
          </div>
          
          <!-- QR 코드 또는 URL 정보 -->
          <div class="mobile-url-info text-center">
            <v-card 
              color="grey-darken-3" 
              variant="tonal" 
              class="pa-4 mx-auto"
              max-width="300"
            >
              <v-card-text class="text-center">
                <v-icon color="grey-lighten-1" class="mb-2">mdi-web</v-icon>
                <div class="text-caption text-grey-lighten-1 mb-2">
                  {{ $t('mobile.accessFromDesktop') }}
                </div>
                <div class="text-body-2 text-white font-weight-medium">
                  bioartlas.com
                </div>
              </v-card-text>
            </v-card>
          </div>
          
          <!-- 최소 해상도 정보 -->
          <div class="mobile-specs text-center mt-6">
            <div class="text-caption text-grey-lighten-2">
              {{ $t('mobile.recommendedResolution') }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 메인 콘텐츠 (데스크톱 전용) -->
    <template v-if="!isMobile">
      <!-- 왼쪽 사이드바 - 인문학적 요소 -->
    <v-navigation-drawer
      permanent
      location="left"
      :width="drawerWidth"
      color="grey-darken-4"
      class="custom-drawer left-drawer elevation-3"
    >
      <v-list class="pa-0">
        <v-list-item class="px-4 py-3 bg-gradient-primary">
          <template v-slot:prepend>
            <v-avatar size="32" color="primary-lighten-2" class="mr-3">
              <v-icon color="white" size="20">mdi-filter-variant</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-h6 text-white font-weight-bold">
            {{ $t('controls.filtering') }}
          </v-list-item-title>
        </v-list-item>
      </v-list>

      <ClusterControls
        :clusters="clusters"
        :selectedClusters="selectedClusters"
        :allArtists="allArtists"
        :selectedArtists="selectedArtists"
        :searchQuery="searchQuery"
        :searchOptions="searchOptions"
        :metadata="metadata"
        :key="$i18n?.locale"
        @update:selectedClusters="selectedClusters = $event"
        @update:selectedArtists="selectedArtists = $event"
        @update:searchQuery="searchQuery = $event"
        @filter-year="filterByYear"
      />
    </v-navigation-drawer>

    <!-- 오른쪽 사이드바 - 기술적 요소 -->
    <v-navigation-drawer
      permanent
      location="right"
      :width="rightDrawerWidth"
      color="grey-darken-4"
      class="custom-drawer right-drawer elevation-3"
    >
      <v-list class="pa-0">
        <v-list-item class="px-4 py-3 bg-gradient-secondary">
          <template v-slot:prepend>
            <v-avatar size="32" color="secondary-lighten-2" class="mr-3">
              <v-icon color="white" size="20">mdi-tune</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title class="text-h6 text-white font-weight-bold">
            {{ $t('controls.controlPanel') }}
          </v-list-item-title>
        </v-list-item>
      </v-list>

      <TechnicalControls
        :clusters="clusters"
        :selectedClusters="selectedClusters"
        :showClusterBorders="showClusterBorders"
        :tooltipDetailMode="tooltipDetailMode"
        :visible-stats="visibleStats"
        :metadata="metadata"
        @reset-view="onResetView"
        @toggle-borders="onToggleBorders"
        @toggle-tooltip-mode="onToggleTooltipMode"
        @take-screenshot="onTakeScreenshot"
      />
    </v-navigation-drawer>

    <!-- 메인 컨텐츠 -->
    <v-main class="main-content-fixed">
      <BioArtUMAP
        ref="umapRef"
        :selectedClusters="selectedClusters"
        :selectedArtists="selectedArtists"
        :searchQuery="searchQuery"
        :stats="stats"
        :loading="loading"
        :showClusterBorders="showClusterBorders"
        :tooltipDetailMode="tooltipDetailMode"
        :yearRange="yearRange"
        @clusters-loaded="clusters = $event"
        @stats-loaded="stats = $event; loading = false"
        @data-loaded="allDataPoints = $event"
        @meta-loaded="onMetaLoaded"
        @take-full-screenshot="onTakeFullScreenshot"
      />
    </v-main>
    </template>

  </v-app>
</template>

<script>
import BioArtUMAP from './components/BioArtUMAP.vue'
import ClusterControls from './components/ClusterControls.vue'
import TechnicalControls from './components/TechnicalControls.vue'
import { getLocalizedArtistName } from './utils/artistTranslation'

export default {
  name: 'App',
  components: {
    BioArtUMAP,
    ClusterControls,
    TechnicalControls
  },
  data() {
    return {
      clusters: {},
      selectedClusters: [],
      stats: null,
      metadata: null,
      loading: true,
      allDataPoints: [], // 전체 데이터 포인트 저장
      
      // 시각화 옵션 중앙 관리
      adjustClusterPositions: false,
      showClusterBorders: false,
      tooltipDetailMode: true,  // true: 상세모드, false: 요약모드
      
      // 필터링 옵션
      yearRange: [1980, 2023],
      selectedArtists: [], // 선택된 작가들
      searchQuery: '', // 아티스트/작품 검색 쿼리
      
      // 모바일 메시지용 데이터
      mobileFeatures: [
        'complexVisualization',
        'multiSidebar',
        'preciseCluster',
        'richTooltips',
        'highResolution'
      ]
    }
  },
  computed: {
    visibleStats() {
      // 현재 필터(선택된 클러스터, 연도 범위, 선택된 작가, 검색어)를 반영한 가시 통계 계산
      const selectedClusterSet = new Set(this.selectedClusters.map(id => String(id)))
      const hasClusterFilter = this.selectedClusters && this.selectedClusters.length > 0

      const filteredPoints = this.allDataPoints.filter(point => {
        // 클러스터 필터
        if (hasClusterFilter && !selectedClusterSet.has(String(point.cluster))) {
          return false
        }
        // 연도 범위 필터: year가 없으면 yearOriginal에서 4자리 파싱하여 적용
        if (Array.isArray(this.yearRange) && this.yearRange.length === 2) {
          const [minYear, maxYear] = this.yearRange
          let ny = null
          if (typeof point.year === 'number' && !isNaN(point.year)) {
            ny = point.year
          } else if (point.yearOriginal || point.year_original) {
            const orig = String(point.yearOriginal || point.year_original)
            const m = orig.match(/\d{4}/)
            if (m) ny = parseInt(m[0], 10)
          }
          if (ny !== null && (ny < minYear || ny > maxYear)) return false
        }
        // 선택된 작가 필터
        if (this.selectedArtists && this.selectedArtists.length > 0) {
          if (!this.selectedArtists.includes(point.artist)) return false
        }
        // 검색어 필터
        if (this.searchQuery && this.searchQuery.trim()) {
          const q = this.searchQuery.trim().toLowerCase()
          const artist = (point.artist || '').toLowerCase()
          const title = (point.title || '').toLowerCase()
          if (!artist.includes(q) && !title.includes(q)) return false
        }
        return true
      })

      const clustersSet = new Set()
      const artistsSet = new Set()

      filteredPoints.forEach(p => {
        clustersSet.add(String(p.cluster))
        if (p.artist && String(p.artist).trim()) {
          artistsSet.add(String(p.artist).trim())
        }
      })

      return {
        clusters: clustersSet.size,
        artworks: filteredPoints.length,
        artists: artistsSet.size
      }
    },
    // 모바일 감지 (디버깅 정보 포함)
    isMobile() {
      const width = window.innerWidth
      const isMobile = width <= 960 // md breakpoint는 960px
      
      // 임시 테스트: 항상 모바일로 인식 (테스트 후 제거 필요)
      // return true
      
      // 디버깅 정보 출력
      console.log('화면 크기 체크:', {
        width,
        isMobile,
        vuetifySmAndDown: this.$vuetify.display.smAndDown,
        vuetifyMdAndUp: this.$vuetify.display.mdAndUp,
        breakpoints: {
          xs: this.$vuetify.display.xs,
          sm: this.$vuetify.display.sm, 
          md: this.$vuetify.display.md,
          lg: this.$vuetify.display.lg,
          xl: this.$vuetify.display.xl
        }
      })
      
      return isMobile
    },

    // 디버깅 정보
    debugInfo() {
      return {
        width: typeof window !== 'undefined' ? window.innerWidth : 0,
        height: typeof window !== 'undefined' ? window.innerHeight : 0,
        userAgent: typeof navigator !== 'undefined' ? navigator.userAgent.slice(0, 50) + '...' : 'N/A'
      }
    },
    
    drawerWidth() {
      if (this.$vuetify.display.xlAndUp) return 320
      if (this.$vuetify.display.lgAndUp) return 300
      return 280
    },
    rightDrawerWidth() {
      if (this.$vuetify.display.xlAndUp) return 300
      if (this.$vuetify.display.lgAndUp) return 280
      return 260
    },
    artistLabelMap() {
      const map = {}
      this.allDataPoints.forEach(point => {
        const artist = (point.artist || '').trim()
        const artistKo = (point.artist_ko || '').trim()
        if (artist && artistKo) {
          map[artist] = artistKo
        }
      })
      return map
    },
    
    // 전체 작가 목록 추출 (작품 수와 클러스터 정보 포함)
    allArtists() {
      const artistsMap = new Map()
      
      this.allDataPoints.forEach(point => {
        if (point.artist && point.artist.trim()) {
          const artistName = point.artist.trim()
          
          if (!artistsMap.has(artistName)) {
            artistsMap.set(artistName, {
              name: artistName,
              nameKo: (point.artist_ko || '').trim(),
              works: [],
              clusters: new Set(),
              yearRange: { min: point.year, max: point.year }
            })
          }
          
          const artist = artistsMap.get(artistName)
          artist.works.push({
            title: point.title,
            year: point.year,
            cluster: point.cluster
          })
          artist.clusters.add(point.cluster)
          artist.yearRange.min = Math.min(artist.yearRange.min, point.year)
          artist.yearRange.max = Math.max(artist.yearRange.max, point.year)
        }
      })
      
      // 배열로 변환하고 현지화된 이름으로 정렬 (A→Z / ㄱ→ㅎ)
      const locale = (this.$i18n && this.$i18n.locale) ? String(this.$i18n.locale) : 'en'
      return Array.from(artistsMap.values())
        .map(artist => ({
          ...artist,
          clusters: Array.from(artist.clusters).sort((a, b) => a - b),
          workCount: artist.works.length,
          yearRangeText: artist.yearRange.min === artist.yearRange.max 
            ? String(artist.yearRange.min) 
            : `${artist.yearRange.min}-${artist.yearRange.max}`
        }))
        .sort((a, b) => {
          const ta = this.translateArtist(a.name)
          const tb = this.translateArtist(b.name)
          return ta.localeCompare(tb, locale, { sensitivity: 'base' })
        })
    },
    
    // 검색 자동완성을 위한 옵션들
    searchOptions() {
      const options = []
      
      // 아티스트명 추가
      this.allArtists.forEach(artist => {
        options.push({
          title: this.translateArtist(artist.name),
          value: artist.name,
          type: 'artist',
          subtitle: `${artist.workCount} ${this.$t('filters.worksCount')}`
        })
      })
      
      // 작품명 추가 (중복 제거)
      const uniqueTitles = new Set()
      this.allDataPoints.forEach(point => {
        if (point.title && point.title.trim() && !uniqueTitles.has(point.title.trim())) {
          uniqueTitles.add(point.title.trim())
          options.push({
            title: point.title.trim(),
            value: point.title.trim(),
            type: 'artwork',
            subtitle: `${this.translateArtist(point.artist)} (${point.year})`
          })
        }
      })
      
      return options.sort((a, b) => a.title.localeCompare(b.title))
    }
  },
  watch: {
    metadata: {
      handler(newMeta) {
        try {
          const yr = newMeta?.statistics?.year_range
          if (typeof yr === 'string' && yr.trim()) {
            const m = yr.match(/\d{4}/g)
            if (m && m.length >= 1) {
              const minY = parseInt(m[0], 10)
              const maxY = parseInt(m[m.length - 1], 10)
              if (isFinite(minY) && isFinite(maxY) && minY <= maxY) {
                this.yearRange = [minY, maxY]
              }
            }
          }
        } catch (e) {
          /* ignore */
        }
      },
      immediate: false
    }
  },
  methods: {
    onMetaLoaded(meta) {
      this.metadata = meta
      try {
        const yr = meta?.statistics?.year_range
        if (typeof yr === 'string' && yr.trim()) {
          const m = yr.match(/\d{4}/g)
          if (m && m.length >= 1) {
            const minY = parseInt(m[0], 10)
            const maxY = parseInt(m[m.length - 1], 10)
            if (isFinite(minY) && isFinite(maxY) && minY <= maxY) {
              this.yearRange = [minY, maxY]
            }
          }
        }
      } catch (e) {
        // ignore
      }
    },
    // 작가 이름 번역 메서드
    translateArtist(artistName) {
      const locale = (this.$i18n && this.$i18n.locale) ? this.$i18n.locale : 'en'
      return getLocalizedArtistName(artistName, this.artistLabelMap, locale)
    },
    
    onResetView() {
      this.$refs.umapRef.resetView()
    },
    
    

    onToggleBorders() {
      this.showClusterBorders = !this.showClusterBorders
      console.log('클러스터 경계선 토글:', this.showClusterBorders)
    },

    onToggleTooltipMode() {
      this.tooltipDetailMode = !this.tooltipDetailMode
      console.log('툴팁 모드 변경:', this.tooltipDetailMode ? '상세 모드 (클릭 시 상세 툴팁)' : '요약 모드 (클릭 시 요약 툴팁 고정)')
    },

    async onTakeScreenshot() {
      // 전체 페이지 스크린샷으로 통일
      await this.onTakeFullScreenshot()
    },

    async onTakeFullScreenshot() {
      try {
        console.log('전체 페이지 스크린샷 시작...')
        
        // 브라우저 화면 공유 API 사용
        if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
          console.log('화면 공유 API 사용')
          
          const stream = await navigator.mediaDevices.getDisplayMedia({ 
            video: { 
              mediaSource: 'screen',
              width: { ideal: 1920 },
              height: { ideal: 1080 }
            } 
          })
          
          const video = document.createElement('video')
          video.srcObject = stream
          video.autoplay = true
          video.muted = true
          
          // 비디오가 로드되면 캔버스에 그리기
          return new Promise((resolve, reject) => {
            video.addEventListener('loadedmetadata', () => {
              // 잠깐 기다린 후 캡처 (화면이 안정화되도록)
              setTimeout(() => {
                try {
                  const canvas = document.createElement('canvas')
                  const ctx = canvas.getContext('2d')
                  
                  canvas.width = video.videoWidth
                  canvas.height = video.videoHeight
                  
                  // 비디오 프레임을 캔버스에 그리기
                  ctx.drawImage(video, 0, 0)
                  
                  // 워터마크 추가
                  ctx.save()
                  ctx.font = '24px Arial'
                  ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'
                  ctx.strokeStyle = 'rgba(0, 0, 0, 0.7)'
                  ctx.lineWidth = 2
                  ctx.textAlign = 'right'
                  ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
                  ctx.shadowBlur = 4
                  
                  const watermark = `BioArtlas - ${new Date().toLocaleDateString('ko-KR')} ${new Date().toLocaleTimeString('ko-KR')}`
                  const x = canvas.width - 30
                  const y = canvas.height - 30
                  
                  ctx.strokeText(watermark, x, y)
                  ctx.fillText(watermark, x, y)
                  ctx.restore()
                  
                  // 스트림 정지
                  stream.getTracks().forEach(track => track.stop())
                  
                  // 다운로드
                  const dataURL = canvas.toDataURL('image/png', 0.95)
                  const link = document.createElement('a')
                  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
                  link.download = `bioartlas-screenshot-${timestamp}.png`
                  link.href = dataURL
                  
                  document.body.appendChild(link)
                  link.click()
                  document.body.removeChild(link)
                  
                  console.log('스크린샷 다운로드 완료:', link.download)
                  resolve()
                  
                } catch (error) {
                  console.error('캔버스 처리 중 오류:', error)
                  reject(error)
                }
              }, 500) // 500ms 대기
            })
            
            video.addEventListener('error', (error) => {
              console.error('비디오 로드 오류:', error)
              reject(error)
            })
          })
          
        } else {
          // API 지원하지 않는 경우
          throw new Error('화면 공유 API를 지원하지 않는 브라우저입니다.')
        }
        
      } catch (error) {
        console.error('화면 공유 스크린샷 실패:', error)
        
        // 사용자에게 안내 메시지 표시
        const message = `
자동 스크린샷이 실패했습니다. 
수동으로 스크린샷을 찍어주세요:

• Windows: Win + Shift + S
• Mac: Cmd + Shift + 4  
• Chrome: F12 > Console > Ctrl + Shift + P > "screenshot"
• Firefox: F12 > Settings(⚙️) > "Take a screenshot"

또는 브라우저의 확장 프로그램을 사용해주세요.
        `
        
        alert(message)
      }
    },


    
    filterByYear(range) {
      // 연도 범위 상태 업데이트
      if (Array.isArray(range) && range.length === 2) {
        const newRange = [Number(range[0]) || 1980, Number(range[1]) || 2023]
        // 새로운 배열로 치환하여 반응성 확실히 트리거
        this.yearRange = [...newRange]
      }
    }
  },
  mounted() {
    // 초기 화면 크기 체크
    console.log('앱 초기화 - 화면 크기 체크:', {
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      isMobile: this.isMobile,
      userAgent: navigator.userAgent
    })
    
    // 화면 크기 변경 감지
    window.addEventListener('resize', () => {
      console.log('화면 크기 변경됨:', {
        width: window.innerWidth,
        height: window.innerHeight,
        isMobile: this.isMobile
      })
      // Vue의 반응성을 트리거하기 위해 강제 업데이트
      this.$forceUpdate()
    })
  }
}
</script>

<style scoped>
/* 메인 레이아웃 */
.main-content-fixed {
  background: linear-gradient(135deg, #121212 0%, #1a1a1a 100%);
  height: 100vh;
  overflow: hidden;
}

/* 사이드바 스타일 */
.custom-drawer {
  border: none !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2) !important;
}

.left-drawer {
  border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

.right-drawer {
  border-left: 1px solid rgba(255, 255, 255, 0.08) !important;
}



/* 사이드바 내부 스크롤바 스타일링 */
.custom-drawer :deep(.v-navigation-drawer__content) {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) rgba(255, 255, 255, 0.05);
}

.custom-drawer :deep(.v-navigation-drawer__content)::-webkit-scrollbar {
  width: 6px;
}

.custom-drawer :deep(.v-navigation-drawer__content)::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
}

.custom-drawer :deep(.v-navigation-drawer__content)::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  transition: background 0.2s ease;
}

.custom-drawer :deep(.v-navigation-drawer__content)::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 미니멀 헤더 */
.bg-gradient-primary {
  background: linear-gradient(135deg, #424242 0%, #303030 100%) !important;
  position: relative;
  overflow: hidden;
}

.bg-gradient-primary::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, rgba(255, 255, 255, 0.05) 0%, transparent 50%);
  pointer-events: none;
}

.bg-gradient-secondary {
  background: linear-gradient(135deg, #424242 0%, #303030 100%) !important;
  position: relative;
  overflow: hidden;
}

.bg-gradient-secondary::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, rgba(255, 255, 255, 0.05) 0%, transparent 50%);
  pointer-events: none;
}

/* 다이얼로그 스타일 */
.dialog-card {
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.detail-section {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

/* 반응형 디자인 */
@media (max-width: 1280px) {
  .custom-drawer {
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15) !important;
  }
}

@media (max-width: 960px) {
  .bg-gradient-primary, .bg-gradient-secondary {
    padding: 8px 12px !important;
  }
}

/* 애니메이션 */
.v-navigation-drawer {
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.v-card {
  transition: all 0.2s ease;
}

.v-avatar {
  transition: all 0.2s ease;
}

.v-avatar:hover {
  transform: scale(1.05);
}

/* 다크 테마 최적화 */
:deep(.v-list-item) {
  border-radius: 8px;
  margin: 4px 8px;
}

:deep(.v-list-item:hover) {
  background: rgba(255, 255, 255, 0.08) !important;
}

:deep(.v-chip) {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

/* 모바일 오버레이 스타일 */
.mobile-overlay {
  background: linear-gradient(135deg, #121212 0%, #1a1a1a 50%, #0d1421 100%) !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100% !important;
  height: 100% !important;
  z-index: 9999 !important;
}

.mobile-message-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
}

.mobile-message-content {
  max-width: 400px;
  width: 100%;
  text-align: center;
}

.mobile-icon-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.mobile-arrow {
  position: absolute;
  bottom: 0;
  right: -20px;
  animation: pulse-arrow 2s infinite ease-in-out;
}

@keyframes pulse-arrow {
  0%, 100% {
    opacity: 0.6;
    transform: translateX(0);
  }
  50% {
    opacity: 1;
    transform: translateX(-10px);
  }
}

.mobile-title {
  background: linear-gradient(45deg, #2196F3, #21CBF3);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.mobile-subtitle {
  line-height: 1.4;
}

.mobile-description .v-chip {
  margin: 4px !important;
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.mobile-url-info .v-card {
  border: 1px solid rgba(33, 150, 243, 0.3);
  background: linear-gradient(135deg, rgba(33, 150, 243, 0.1), rgba(33, 203, 243, 0.05)) !important;
}

.mobile-specs {
  opacity: 0.7;
  font-style: italic;
}

/* 모바일 세로 화면 최적화 */
@media (max-height: 600px) {
  .mobile-message-content {
    transform: scale(0.9);
  }
  
  .mobile-icon-container {
    margin-bottom: 16px !important;
  }
  
  .mobile-icon-container .v-icon:first-child {
    font-size: 80px !important;
  }
  
  .mobile-arrow {
    font-size: 60px !important;
  }
}

/* 매우 작은 화면 대응 */
@media (max-width: 360px) {
  .mobile-message-container {
    padding: 16px;
  }
  
  .mobile-title {
    font-size: 1.8rem !important;
  }
  
  .mobile-subtitle {
    font-size: 1.1rem !important;
  }
}
</style> 
