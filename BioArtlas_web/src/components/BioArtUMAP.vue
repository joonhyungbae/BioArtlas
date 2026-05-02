<template>
  <div class="umap-wrapper">
      <div ref="canvasContainer" class="umap-container">
    <canvas ref="mainCanvas" class="main-canvas" />
    

  </div>
    
    <!-- 로딩 오버레이 -->
    <v-overlay :model-value="loading" class="d-flex align-center justify-center">
      <div class="text-center">
        <v-progress-circular
          indeterminate
          size="64"
          color="grey-lighten-1"
          class="mb-4"
        ></v-progress-circular>
        <div class="text-h6 text-white">{{ $t('loading.umapCalculating') }}</div>
        <div class="text-caption text-grey-lighten-1 mt-2">{{ $t('loading.analyzingArtworks') }}</div>
      </div>
    </v-overlay>

    <!-- 호버 툴팁 (항상 요약 정보) -->
    <div
      v-if="hoverTooltip.visible"
      class="hover-tooltip"
      :style="{
        left: hoverTooltip.position.x + 'px',
        top: hoverTooltip.position.y + 'px'
      }"
    >
      <v-card
        dark
        color="grey-darken-4"
        elevation="12"
        class="hover-tooltip-card"
        min-width="200"
        max-width="280"
      >
        <v-card-text class="pa-3">
          <div class="hover-tooltip-content">
            <div class="text-body-2 font-weight-bold text-white mb-1">
              {{ hoverTooltip.point?.title || $t('common.noTitle') }}
            </div>
            <div class="text-caption text-grey-lighten-2 mb-1">
              <v-icon size="12" class="mr-1">mdi-account</v-icon>
              {{ hoverTooltip.point?.artist ? translateArtist(hoverTooltip.point.artist) : $t('common.unknownArtist') }}
            </div>
            <div class="text-caption text-grey-lighten-2 mb-1">
              <v-icon size="12" class="mr-1">mdi-calendar</v-icon>
              {{ formatYear(hoverTooltip.point) }}
            </div>
            <!-- 장르는 데이터에서 제거되었으므로 표시하지 않음 -->
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- 클릭된 작품 정보 툴팁 -->
    <div
      v-for="tooltip in activeTooltips"
      :key="tooltip.id"
      class="artwork-tooltip"
      :style="{
        left: tooltip.position.x + 'px',
        top: tooltip.position.y + 'px'
      }"
    >
      <!-- 상세 모드: 완전한 상세 툴팁 -->
      <v-card
        v-if="tooltipDetailMode"
        dark
        color="grey-darken-3"
        elevation="8"
        class="tooltip-card d-flex flex-column"
        min-width="300"
        max-width="380"
        max-height="500"
      >
        <v-card-title 
          class="bg-grey-darken-4 pa-2 d-flex align-center justify-space-between tooltip-drag-handle"
          :class="{ 
            'dragging': tooltipDragging.isDragging && tooltipDragging.tooltipId === tooltip.id,
            'manually-positioned': tooltip.isDraggedManually
          }"
          @mousedown="startTooltipDrag($event, tooltip.id)"
          @dblclick="resetTooltipPosition(tooltip.id)"
        >
          <div class="d-flex align-center flex-grow-1 min-width-0">
            <v-avatar size="20" color="grey-lighten-1" class="mr-2 flex-shrink-0">
              <v-icon color="grey-darken-3" size="14">
                {{ tooltip.isDraggedManually ? 'mdi-pin' : 'mdi-drag' }}
              </v-icon>
            </v-avatar>
            <div class="text-body-1 font-weight-bold text-white text-truncate">
              {{ tooltip.point.title }}
            </div>
          </div>
          <v-btn
            @click="closeTooltip(tooltip.id)"
            @mousedown.stop
            icon
            size="x-small"
            variant="text"
            color="white"
            class="flex-shrink-0 ml-1"
          >
            <v-icon size="14">mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        
        <v-card-text class="pa-2 flex-1-1 overflow-y-auto">
          <div class="d-flex flex-wrap gap-1 mb-2">
            <v-chip size="x-small" color="grey-lighten-1" variant="tonal" density="compact">
              <v-icon left size="10">mdi-account</v-icon>
              <span class="text-caption">{{ translateArtist(tooltip.point.artist) }}</span>
            </v-chip>
            <v-chip size="x-small" color="grey-lighten-1" variant="tonal" density="compact">
              <v-icon left size="10">mdi-calendar</v-icon>
              <span class="text-caption">{{ formatYear(tooltip.point) }}</span>
            </v-chip>

          </div>
          
          <div class="tooltip-details">
            <div class="detail-item mb-1">
              <span class="text-caption text-grey-lighten-1">{{ $t('tooltip.cluster') }}:</span>
              <span class="text-caption text-white font-weight-medium ml-1">
                {{ clusters[tooltip.point.cluster]?.name }}
              </span>
            </div>
            <!-- 페이지 네비게이션 -->
            <div class="d-flex align-center mb-1">
              <v-btn size="x-small" variant="text" color="grey-lighten-2" @mousedown.stop @click.stop="prevTooltipPage(tooltip.id)">«</v-btn>
              <span class="text-caption text-grey-lighten-2 mx-2">{{ getTooltipPage(tooltip.id) + 1 }}/2</span>
              <v-btn size="x-small" variant="text" color="grey-lighten-2" @mousedown.stop @click.stop="nextTooltipPage(tooltip.id)">»</v-btn>
            </div>
            <!-- 13개 축 동적 표시 (페이지당 7/6 분할) -->
            <div v-for="axis in axesForPage(getTooltipPage(tooltip.id))" :key="`axis-${axis}`" class="detail-item mb-1">
              <span class="text-caption text-grey-lighten-1" v-html="formatAxisLabel(axis)"></span>

              <!-- 접힘 상태: 첫 토큰 Chip + +N more Chip -->
              <span v-if="!isAxisExpanded(tooltip.id, axis)" class="ml-1" style="display:inline-flex; align-items:center; gap:4px; flex-wrap:wrap;">
                <v-chip size="x-small" density="compact" variant="tonal" color="grey-lighten-1">
                  {{ summarizeAxisValue(tooltip.point, axis) }}
                </v-chip>
                <v-chip
                  v-if="axisHasMore(tooltip.point, axis)"
                  size="x-small"
                  density="compact"
                  variant="outlined"
                  color="grey-lighten-2"
                  @mousedown.stop
                  @click.stop="expandAxis(tooltip.id, axis)"
                >
                  +{{ axisMoreCount(tooltip.point, axis) }} more
                </v-chip>
              </span>

              <!-- 펼침 상태: 모든 토큰을 Chip으로 -->
              <div v-else class="mt-1" style="display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
                <v-chip
                  v-for="tok in tokenizeAxisValue(tooltip.point, axis)"
                  :key="`tok-${axis}-${tok}`"
                  size="x-small"
                  density="compact"
                  variant="tonal"
                  color="grey-lighten-1"
                >
                  {{ tok }}
                </v-chip>
                <v-chip
                  size="x-small"
                  density="compact"
                  variant="text"
                  color="grey-lighten-2"
                  @mousedown.stop
                  @click.stop="collapseAxis(tooltip.id, axis)"
                >
                  less
                </v-chip>
              </div>
            </div>
          </div>
        </v-card-text>
      </v-card>

      <!-- 요약 모드: 고정된 요약 툴팁 -->
      <v-card
        v-else
        dark
        color="grey-darken-3"
        elevation="8"
        class="tooltip-card summary-fixed-tooltip"
        min-width="250"
        max-width="300"
      >
        <v-card-title 
          class="bg-grey-darken-4 pa-2 d-flex align-center justify-space-between tooltip-drag-handle"
          :class="{ 
            'dragging': tooltipDragging.isDragging && tooltipDragging.tooltipId === tooltip.id,
            'manually-positioned': tooltip.isDraggedManually
          }"
          @mousedown="startTooltipDrag($event, tooltip.id)"
          @dblclick="resetTooltipPosition(tooltip.id)"
        >
          <div class="d-flex align-center flex-grow-1 min-width-0">
            <v-avatar size="18" color="primary-lighten-2" class="mr-2 flex-shrink-0">
              <v-icon color="white" size="12">
                {{ tooltip.isDraggedManually ? 'mdi-pin' : 'mdi-drag' }}
              </v-icon>
            </v-avatar>
            <div class="text-body-2 font-weight-bold text-white text-truncate">
              {{ tooltip.point.title }}
            </div>
          </div>
          <v-btn
            @click="closeTooltip(tooltip.id)"
            @mousedown.stop
            icon
            size="x-small"
            variant="text"
            color="white"
            class="flex-shrink-0 ml-1"
          >
            <v-icon size="12">mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        
        <v-card-text class="pa-3">
          <div class="summary-tooltip-content">
            <div class="text-caption text-grey-lighten-2 mb-1">
              <v-icon size="12" class="mr-1">mdi-account</v-icon>
              {{ translateArtist(tooltip.point.artist) }}
            </div>
            <div class="text-caption text-grey-lighten-2 mb-1">
              <v-icon size="12" class="mr-1">mdi-calendar</v-icon>
              {{ formatYear(tooltip.point) }}
            </div>
            <!-- 장르는 데이터에서 제거되었으므로 표시하지 않음 -->
            <div class="text-caption text-grey-lighten-2">
              <v-icon size="12" class="mr-1">mdi-circle-multiple</v-icon>
              {{ clusters[tooltip.point.cluster]?.name || 'N/A' }}
            </div>

          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- 모든 툴팁 닫기 버튼 -->
    <v-btn
      v-if="activeTooltips.length > 0"
      @click="closeAllTooltips"
      color="red-darken-2"
      variant="elevated"
      size="small"
      class="close-all-tooltips-btn"
      elevation="6"
    >
      <v-icon start size="small">mdi-close-box-multiple</v-icon>
      {{ $t('controls.closeAllTooltips') }} ({{ activeTooltips.length }})
    </v-btn>
  </div>
</template>

<script>
import { getLocalizedArtistName } from '../utils/artistTranslation'

export default {
  name: 'BioArtUMAP',
  props: {
    selectedClusters: {
      type: Array,
      default: () => []
    },
    selectedArtists: {
      type: Array,
      default: () => []
    },
    searchQuery: {
      type: String,
      default: ''
    },
    adjustClusterPositions: {
      type: Boolean,
      default: false
    },
    showClusterBorders: {
      type: Boolean,
      default: false
    },
    yearRange: {
      type: Array,
      default: () => [1980, 2023]
    },
    tooltipDetailMode: {
      type: Boolean,
      default: true  // true: 상세모드, false: 요약모드
    }
  },
  emits: ['clusters-loaded', 'point-selected', 'stats-loaded', 'data-loaded', 'meta-loaded'],
  data() {
    return {
      loading: true,
      dataPoints: [],
      clusters: {},
      stats: null,
      
      // Canvas 관련
      canvas: null,
      ctx: null,
      
      // 뷰포트 관련
      viewport: {
        x: 0,
        y: 0,
        scale: 1,
        width: 800,
        height: 600
      },
      

      
      // 인터랙션 관련
      isDragging: false,
      lastMousePos: { x: 0, y: 0 },
      hoveredPoint: null,
      
      // 툴팁 관련
      hoverTooltip: {
        visible: false,
        point: null,
        position: { x: 0, y: 0 }
      },
      
      // 다중 툴팁 지원
      activeTooltips: [],
      tooltipIdCounter: 0,
      
      // 툴팁 드래그 관련
      tooltipDragging: {
        isDragging: false,
        tooltipId: null,
        startPos: { x: 0, y: 0 },
        initialTooltipPos: { x: 0, y: 0 }
      },
      
      // 성능 최적화
      renderRequestId: null,
      needsRedraw: true,
      
      // 애니메이션 효과 관련
      animationTime: 0,
      energyParticles: [], // 클러스터간 에너지 흐름을 위한 파티클들
      breathingSeeds: new Map(), // 각 포인트의 고유 숨쉬기 시드
      
      adjustedPoints: [],
      
      // 클릭 타이머
      clickTimeout: null,
      
      // 메타데이터 축 목록(13개 축)
      metadataAxes: [],
      // 메타 누락 시 사용할 기본 축 목록
      defaultAxes: [
        'Materiality',
        'Methodology',
        'Actor Relationships & Configuration',
        'Ethical Approach',
        'Aesthetic Strategy',
        'Epistemic Function',
        'Philosophical Stance',
        'Social Context',
        'Audience Engagement',
        'Temporal Scale',
        'Spatio Scale',
        'Power and Capital Critique',
        'Documentation & Representation'
      ],
      // 축별 펼침 상태: key = `${tooltipId}|${axisName}`
      expandedAxes: new Set(),
      tooltipPages: new Map() // tooltipId -> 0 or 1
    }
  },
  computed: {
    artistLabelMap() {
      const map = {}
      this.dataPoints.forEach(point => {
        const artist = (point.artist || '').trim()
        const artistKo = (point.artist_ko || '').trim()
        if (artist && artistKo) {
          map[artist] = artistKo
        }
      })
      return map
    }
  },
  mounted() {
    this.initCanvas()
    this.loadData()
    this.initAnimationSystem()
    window.addEventListener('resize', this.onWindowResize)
    document.addEventListener('click', this.onDocumentClick)
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.onWindowResize)
    document.removeEventListener('click', this.onDocumentClick)
    
    // 툴팁 드래그 이벤트 리스너 정리
    document.removeEventListener('mousemove', this.onTooltipDrag)
    document.removeEventListener('mouseup', this.endTooltipDrag)
    
    if (this.renderRequestId) {
      cancelAnimationFrame(this.renderRequestId)
    }
    if (this.clickTimeout) {
      clearTimeout(this.clickTimeout)
    }
    
    // 드래그 관련 스타일 복원
    document.body.style.userSelect = ''
    document.body.style.cursor = ''
  },
  watch: {
    selectedClusters: {
      handler() {
        this.needsRedraw = true
        this.requestRender()
      },
      deep: true
    },
    selectedArtists: {
      handler() {
        this.needsRedraw = true
        this.requestRender()
      },
      deep: true
    },
    yearRange: {
      handler() {
        this.needsRedraw = true
        this.requestRender()
      },
      deep: true
    },
    searchQuery: {
      handler() {
        this.needsRedraw = true
        this.requestRender()
      }
    },
    adjustClusterPositions: {
      handler(newVal) {
        if (this.dataPoints.length > 0) {
          if (newVal) {
            // 클러스터 조정 활성화
            this.adjustedPoints = JSON.parse(JSON.stringify(this.dataPoints))
            this.performClusterAdjustment()
          } else {
            // 클러스터 조정 비활성화 - 원본 데이터 복사
            this.adjustedPoints = JSON.parse(JSON.stringify(this.dataPoints))
          }
          // 애니메이션 시스템 재초기화
          this.initBreathingSeeds()
          this.createEnergyParticles()
          
          this.fitViewport()
          this.needsRedraw = true
          this.requestRender()
        }
      },
      immediate: true
    },
    showClusterBorders: {
      handler() {
        this.needsRedraw = true
        this.requestRender()
      }
    },
    tooltipDetailMode: {
      handler() {
        // 모드가 변경되면 기존 툴팁들의 표시 방식이 바뀌므로 즉시 반영
        console.log('툴팁 모드 변경됨:', this.tooltipDetailMode ? '상세 모드' : '요약 모드')
      }
    },
    activeTooltips: {
      handler() {
        // 툴팁이 변경될 때마다 선택 기반 연결 파티클 재생성
        if (this.dataPoints && this.dataPoints.length > 0) {
          this.createEnergyParticles()
          // 선택 상태가 변경되면 숨쉬기 강도도 재계산 (선택된 작품이 더 활발하게)
          this.initBreathingSeeds()
        }
      },
      deep: true
    }
  },
  methods: {
    // 연도 숫자 파싱 (year가 null일 때 yearOriginal에서 4자리 추출)
    getNumericYear(point) {
      if (!point) return null
      const y = point.year
      if (typeof y === 'number' && !isNaN(y)) return y
      const orig = point.yearOriginal || point.year_original
      if (orig && typeof orig === 'string') {
        const match = orig.match(/\d{4}/)
        if (match) {
          const num = parseInt(match[0], 10)
          return isNaN(num) ? null : num
        }
      }
      return null
    },
    getTooltipPage(tooltipId) {
      return this.tooltipPages.get(tooltipId) || 0
    },
    setTooltipPage(tooltipId, page) {
      const p = Math.max(0, Math.min(1, page))
      this.tooltipPages.set(tooltipId, p)
      // 강제 업데이트(맵은 반응성이 약하므로)
      this.$forceUpdate()
    },
    nextTooltipPage(tooltipId) {
      this.setTooltipPage(tooltipId, (this.getTooltipPage(tooltipId) + 1) % 2)
    },
    prevTooltipPage(tooltipId) {
      this.setTooltipPage(tooltipId, (this.getTooltipPage(tooltipId) + 1) % 2)
    },
    axesForPage(pageIdx) {
      const axes = this.metadataAxes && this.metadataAxes.length > 0 ? this.metadataAxes : this.defaultAxes
      const first = axes.slice(0, 7)
      const second = axes.slice(7)
      return pageIdx === 0 ? first : second
    },
    formatAxisLabel(axisName) {
      if (!axisName || typeof axisName !== 'string') return ''
      const locale = (this.$i18n && this.$i18n.locale) ? String(this.$i18n.locale) : 'en'
      const isKo = locale.toLowerCase().startsWith('ko')
      if (isKo) {
        const koMap = {
          'Materiality': '물질성',
          'Methodology': '방법론',
          'Actor Relationships & Configuration': '행위자 관계 및 구성',
          'Ethical Approach': '윤리적 접근 방식',
          'Aesthetic Strategy': '미학적 전략',
          'Epistemic Function': '인식론적 기능',
          'Philosophical Stance': '철학적 입장',
          'Social Context': '사회적 맥락',
          'Audience Engagement': '관객 참여방식',
          'Temporal Scale': '시간적 스케일',
          'Spatio Scale': '공간적 스케일',
          'Power and Capital Critique': '권력 및 자본 비판',
          'Documentation & Representation': '문서화와 재현'
        }
        const label = koMap[axisName] || axisName
        return `${label}:`
      }
      const tokens = axisName.split(' ').filter(Boolean)
      if (tokens.length <= 1) return `${axisName}:`
      // '&'가 포함되면 '&'까지 1행, 나머지 2행
      const ampIdx = tokens.findIndex(t => t === '&')
      if (ampIdx !== -1 && ampIdx < tokens.length - 1) {
        const line1 = tokens.slice(0, ampIdx + 1).join(' ')
        const line2 = tokens.slice(ampIdx + 1).join(' ')
        return `${line1}<br/>${line2}:`
      }
      // 그 외에는 절반 지점에서 줄바꿈
      const splitAt = Math.ceil(tokens.length / 2)
      const line1 = tokens.slice(0, splitAt).join(' ')
      const line2 = tokens.slice(splitAt).join(' ')
      return `${line1}<br/>${line2}:`
    },
    // 축 값 토큰화
    tokenizeAxisValue(point, axisName) {
      const v = this.getAxisDisplayValue(point, axisName)
      if (!v || typeof v !== 'string') return []
      return v.split(',').map(s => s.trim()).filter(Boolean)
    },
    summarizeAxisValue(point, axisName) {
      const toks = this.tokenizeAxisValue(point, axisName)
      return toks.length > 0 ? toks[0] : '-'
    },
    fullAxisValue(point, axisName) {
      const toks = this.tokenizeAxisValue(point, axisName)
      return toks.length > 0 ? toks.join(', ') : '-'
    },
    axisHasMore(point, axisName) {
      const toks = this.tokenizeAxisValue(point, axisName)
      return toks.length > 1
    },
    axisMoreCount(point, axisName) {
      const toks = this.tokenizeAxisValue(point, axisName)
      return Math.max(0, toks.length - 1)
    },
    isAxisExpanded(tooltipId, axisName) {
      return this.expandedAxes.has(`${tooltipId}|${axisName}`)
    },
    expandAxis(tooltipId, axisName) {
      this.expandedAxes.add(`${tooltipId}|${axisName}`)
    },
    collapseAxis(tooltipId, axisName) {
      this.expandedAxes.delete(`${tooltipId}|${axisName}`)
    },
    getAxisDisplayValue(point, axisName) {
      if (!point || !axisName) return '—'
      const locale = (this.$i18n && this.$i18n.locale) ? String(this.$i18n.locale) : 'en'
      const isKo = locale.toLowerCase().startsWith('ko')
      if (isKo) {
        // 한국어 우선: axes_ko → 평탄화된 *_ko → 영어로 폴백
        const ko = point.axes_ko && point.axes_ko[axisName]
        if (ko && String(ko).trim()) return String(ko)
        const flatKo = point[`${axisName}_ko`]
        if (flatKo && String(flatKo).trim()) return String(flatKo)
      }
      // 영어 값 사용
      const en = point.axes_en && point.axes_en[axisName]
      if (en && String(en).trim()) return String(en)
      const flat = point[axisName]
      if (flat && String(flat).trim()) return String(flat)
      return '—'
    },
    // 장르 제거: 더 이상 사용하지 않음 (남겨둔 호출부도 제거됨)
    formatYear(point) {
      if (!point) return 'N/A'
      const y = point.year
      if (typeof y === 'number' && !isNaN(y)) {
        return `${y}${this.$t('common.year')}`
      }
      // 새로운 JSON 키 우선: yearOriginal (카멜케이스), 하위호환: year_original
      const orig = point.yearOriginal || point.year_original
      if (orig && String(orig).trim()) {
        return String(orig).trim()
      }
      return 'N/A'
    },
    // 작가 이름 번역 메서드
    translateArtist(artistName) {
      const locale = (this.$i18n && this.$i18n.locale) ? this.$i18n.locale : 'en'
      return getLocalizedArtistName(artistName, this.artistLabelMap, locale)
    },
    
    initCanvas() {
      const container = this.$refs.canvasContainer
      this.viewport.width = container.clientWidth
      this.viewport.height = container.clientHeight
      
      this.canvas = this.$refs.mainCanvas
      this.ctx = this.canvas.getContext('2d')
      
      // 기본 커서 설정
      this.canvas.style.cursor = 'grab'
      
      this.resizeCanvas()
      
      // 이벤트 리스너
      this.canvas.addEventListener('mousedown', this.onMouseDown)
      this.canvas.addEventListener('mousemove', this.onMouseMove)
      this.canvas.addEventListener('mouseup', this.onMouseUp)
      this.canvas.addEventListener('mouseleave', this.onMouseLeave)
      this.canvas.addEventListener('wheel', this.onWheel)
      this.canvas.addEventListener('click', this.onClick)
      this.canvas.addEventListener('dblclick', this.onDoubleClick) // 더블클릭 이벤트 추가
      this.canvas.addEventListener('auxclick', this.onAuxClick) // 휠 버튼 클릭 추가
    },
    
    resizeCanvas() {
      const container = this.$refs.canvasContainer
      this.viewport.width = container.clientWidth
      this.viewport.height = container.clientHeight
      
      this.canvas.width = this.viewport.width
      this.canvas.height = this.viewport.height
      
      this.needsRedraw = true
      this.requestRender()
    },
    
    async loadData() {
      try {
        const response = await fetch('/bioart_clustering_2d.json')
        const data = await response.json()
        
        this.dataPoints = data.points
        this.clusters = data.clusters
        this.stats = data.metadata.statistics
        // 메타데이터 전달 (클러스터링/시각화 설정 포함)
        this.$emit('meta-loaded', data.metadata)
        
        // 13개 축 목록 설정: metadata.axes 우선, 없으면 첫 포인트의 axes_en 키 사용, 그래도 없으면 기본 축
        const axesFromMeta = Array.isArray(data?.metadata?.axes) ? data.metadata.axes : []
        let axes = axesFromMeta
        if (!axes || axes.length === 0) {
          const first = (this.dataPoints && this.dataPoints.length > 0) ? this.dataPoints[0] : null
          const enObj = first && first.axes_en ? first.axes_en : null
          axes = enObj ? Object.keys(enObj) : []
        }
        this.metadataAxes = Array.isArray(axes) && axes.length > 0 ? axes : this.defaultAxes
        
        // 조정된 포인트 초기화
        this.adjustedPoints = JSON.parse(JSON.stringify(this.dataPoints))
        
        // 클러스터 위치 조정이 기본값이면 자동 실행
        if (this.adjustClusterPositions) {
          console.log('초기 로딩: 클러스터 조정 시작')
          this.performClusterAdjustment()
          console.log('초기 로딩: 클러스터 조정 완료')
        }
        
        // 2D UMAP 좌표는 이미 umapX, umapY로 저장되어 있음
        // 클러스터 조정 후 뷰포트를 다시 맞춤
        this.fitViewport()
        
        this.$emit('clusters-loaded', this.clusters)
        this.$emit('stats-loaded', this.stats)
        this.$emit('data-loaded', this.dataPoints)
        
        // 애니메이션 시스템 초기화
        this.initBreathingSeeds()
        this.createEnergyParticles()
        
        this.loading = false
        
        this.needsRedraw = true
        this.requestRender()
        
        // 초기 로딩 완료 후 조정된 상태 확실히 렌더링
        this.$nextTick(() => {
          console.log('초기 로딩: 최종 렌더링 트리거 (애니메이션 포함)')
          this.needsRedraw = true
          this.requestRender()
        })
      } catch (error) {
        console.error('데이터 로딩 실패:', error)
        this.loading = false
      }
    },
    

    
    fitViewport() {
      if (!this.dataPoints.length) return
      
      // 조정된 포인트 또는 원본 포인트 사용
      const basePoints = this.adjustClusterPositions ? this.adjustedPoints : this.dataPoints
      
      // 표시할 포인트들 (모든 클러스터 포함)
      const visiblePoints = basePoints
      
      if (visiblePoints.length === 0) return
      
      const xValues = visiblePoints.map(p => p.umapX)
      const yValues = visiblePoints.map(p => p.umapY)
      
      const xRange = { min: Math.min(...xValues), max: Math.max(...xValues) }
      const yRange = { min: Math.min(...yValues), max: Math.max(...yValues) }
      
      const dataWidth = xRange.max - xRange.min
      const dataHeight = yRange.max - yRange.min
      
      // 적절한 패딩으로 모든 클러스터가 보이도록 설정
      const padding = 0.1 // 10% 패딩
      const scaleX = this.viewport.width / (dataWidth * (1 + padding))
      const scaleY = this.viewport.height / (dataHeight * (1 + padding))
      
      // 더 적절한 스케일 설정
      this.viewport.scale = Math.min(scaleX, scaleY) * 0.9
      
      // 중앙 정렬을 위해 뷰포트 위치 조정
      const centerX = (xRange.min + xRange.max) / 2
      const centerY = (yRange.min + yRange.max) / 2
      
      this.viewport.x = (this.viewport.width / 2) - (centerX * this.viewport.scale)
      this.viewport.y = (this.viewport.height / 2) - (centerY * this.viewport.scale)
    },
    
    getOptimalScale() {
      if (!this.dataPoints.length) return 1
      
      // 조정된 포인트 또는 원본 포인트 사용
      const basePoints = this.adjustClusterPositions ? this.adjustedPoints : this.dataPoints
      
      // 표시할 포인트들 (모든 클러스터 포함)
      const visiblePoints = basePoints
      
      if (visiblePoints.length === 0) return 1
      
      const xValues = visiblePoints.map(p => p.umapX)
      const yValues = visiblePoints.map(p => p.umapY)
      
      const xRange = { min: Math.min(...xValues), max: Math.max(...xValues) }
      const yRange = { min: Math.min(...yValues), max: Math.max(...yValues) }
      
      const dataWidth = xRange.max - xRange.min
      const dataHeight = yRange.max - yRange.min
      
      // 적절한 패딩으로 모든 클러스터가 보이도록 설정
      const padding = 0.1 // 10% 패딩
      const scaleX = this.viewport.width / (dataWidth * (1 + padding))
      const scaleY = this.viewport.height / (dataHeight * (1 + padding))
      
      // 최적 스케일 반환
      return Math.min(scaleX, scaleY) * 0.9
    },
    
    resetView() {
      // 항상 현재 데이터 상태에 맞는 최적의 뷰를 계산
      this.fitViewport()
      this.needsRedraw = true
      this.requestRender()
    },
    
    requestRender() {
      if (this.renderRequestId) {
        cancelAnimationFrame(this.renderRequestId)
      }
      this.renderRequestId = requestAnimationFrame(() => {
        if (this.needsRedraw) {
          this.render()
          this.needsRedraw = false
        }
      })
    },
    
    render() {
      const ctx = this.ctx
      ctx.clearRect(0, 0, this.viewport.width, this.viewport.height)
      
      // 배경
      this.renderBackground()
      
      // 에너지 흐름 (포인트들 뒤에 렌더링)
      this.renderEnergyFlow()
      
      // 클릭된 점들 간의 거리선 렌더링 (포인트들 아래층)
      this.renderDistanceLines()
      
      // 포인트들
      this.renderPoints()
      
      // 툴팁 위치 업데이트
      this.updateTooltipPositions()
    },
    
    renderBackground() {
      const ctx = this.ctx
      
      // Dark 테마 그라데이션 배경
      const gradient = ctx.createLinearGradient(0, 0, 0, this.viewport.height)
      gradient.addColorStop(0, '#1a1a1a')
      gradient.addColorStop(1, '#121212')
      
      ctx.fillStyle = gradient
      ctx.fillRect(0, 0, this.viewport.width, this.viewport.height)
      
      // 그리드 패턴 (옵션)
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)'
      ctx.lineWidth = 1
      
      const gridSize = 50
      for (let x = 0; x < this.viewport.width; x += gridSize) {
        ctx.beginPath()
        ctx.moveTo(x, 0)
        ctx.lineTo(x, this.viewport.height)
        ctx.stroke()
      }
      
      for (let y = 0; y < this.viewport.height; y += gridSize) {
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(this.viewport.width, y)
        ctx.stroke()
      }
    },
    
    renderPoints() {
      const ctx = this.ctx
      
      // 조정된 포인트 또는 원본 포인트 사용
      const pointsToRender = this.adjustClusterPositions ? this.adjustedPoints : this.dataPoints
      
      // 필터링된 포인트들을 저장할 배열 (경계선 그리기용)
      const visiblePoints = []
      
      
      
      pointsToRender.forEach(point => {
        // 선택된 클러스터 필터링 (선택된 클러스터가 있을 때만)
        if (this.selectedClusters.length > 0 && !this.selectedClusters.includes(String(point.cluster))) {
          return
        }
        
        // 연도 범위 필터링 (year가 null이면 yearOriginal에서 파싱하여 적용)
        {
          const ny = this.getNumericYear(point)
          if (ny !== null && (ny < this.yearRange[0] || ny > this.yearRange[1])) {
            return
          }
        }
        
        // 선택된 작가 필터링 (선택된 작가가 있을 때만)
        if (this.selectedArtists.length > 0 && !this.selectedArtists.includes(point.artist)) {
          return
        }
        
        // 검색 쿼리 필터링
        if (this.searchQuery && this.searchQuery.trim()) {
          const searchText = this.searchQuery.toLowerCase().trim()
          const artistMatch = (point.artist || '').toLowerCase().includes(searchText)
          const titleMatch = (point.title || '').toLowerCase().includes(searchText)
          
          if (!artistMatch && !titleMatch) {
            return
          }
        }
        
        // UMAP 좌표 유효성 검사 (0도 허용, 유한 수만 허용)
        if (typeof point.umapX !== 'number' || typeof point.umapY !== 'number' ||
            !isFinite(point.umapX) || !isFinite(point.umapY)) {
          return
        }

        // 모든 필터링 조건을 통과한 포인트를 저장 (경계선 그리기용)
        visiblePoints.push(point)
        
        const cluster = this.clusters[point.cluster]
        const screenPos = this.worldToScreen(point.umapX, point.umapY)
        
        // 스크린 좌표 유효성 검사
        if (isNaN(screenPos.x) || isNaN(screenPos.y) ||
            !isFinite(screenPos.x) || !isFinite(screenPos.y)) {
          return
        }
        
        // 포인트 숨쉬기 애니메이션 효과
        const pointKey = `${point.title}-${point.artist}-${point.cluster}`
        let breathingMultiplier = 1
        
        if (this.breathingSeeds.has(pointKey)) {
          const seed = this.breathingSeeds.get(pointKey)
          const breathingValue = Math.sin(this.animationTime * seed.frequency + seed.phase) * seed.amplitude
          breathingMultiplier = 1 + breathingValue
        }
        
        // 미니멀하고 세련된 포인트 크기 (숨쉬기 효과 적용)
        const baseRadius = 5 * breathingMultiplier
        const hoverRadius = this.hoveredPoint === point ? baseRadius + 2 : baseRadius
        
        // 클릭된 점인지 확인 (활성 툴팁이 있는 점)
        const isClickedPoint = this.activeTooltips.some(tooltip => 
          tooltip.point.title === point.title && 
          tooltip.point.artist === point.artist &&
          tooltip.point.cluster === point.cluster
        )
        
        // 클릭된 점의 흰색 글로우 효과
        if (isClickedPoint) {
          const time = Date.now() * 0.003
          const glowIntensity = (Math.sin(time) + 1) * 0.5 // 0~1 범위로 펄스
          
          // 외부 글로우 (가장 큰 원)
          ctx.beginPath()
          ctx.arc(screenPos.x, screenPos.y, hoverRadius + 8 + glowIntensity * 3, 0, 2 * Math.PI)
          ctx.strokeStyle = `rgba(255, 255, 255, ${0.15 + glowIntensity * 0.1})`
          ctx.lineWidth = 2
          ctx.stroke()
          
          // 중간 글로우
          ctx.beginPath()
          ctx.arc(screenPos.x, screenPos.y, hoverRadius + 5 + glowIntensity * 2, 0, 2 * Math.PI)
          ctx.strokeStyle = `rgba(255, 255, 255, ${0.25 + glowIntensity * 0.15})`
          ctx.lineWidth = 1.5
          ctx.stroke()
          
          // 내부 글로우 (가장 밝음)
          ctx.beginPath()
          ctx.arc(screenPos.x, screenPos.y, hoverRadius + 2 + glowIntensity, 0, 2 * Math.PI)
          ctx.strokeStyle = `rgba(255, 255, 255, ${0.4 + glowIntensity * 0.2})`
          ctx.lineWidth = 1
          ctx.stroke()
        }
        
        // Cluster 0 전용 특수 효과 제거: 모든 클러스터 동일 스타일
        
        // 미니멀한 그림자 효과
        const shadowIntensity = this.hoveredPoint === point ? 0.5 : 0.2
        ctx.shadowColor = `rgba(0, 0, 0, ${shadowIntensity})`
        ctx.shadowBlur = this.hoveredPoint === point ? 6 : 3
        ctx.shadowOffsetX = 0.5
        ctx.shadowOffsetY = 0.5
        
        // 메인 포인트 그리기
        ctx.beginPath()
        ctx.arc(screenPos.x, screenPos.y, hoverRadius, 0, 2 * Math.PI)
        
        // 세련된 그라데이션 효과
        const lightDirection = 0.3 // 광원 방향
        const gradientX = screenPos.x - hoverRadius * lightDirection
        const gradientY = screenPos.y - hoverRadius * lightDirection
        
        // 그라데이션 좌표 유효성 검사
        if (isNaN(gradientX) || isNaN(gradientY) || 
            !isFinite(gradientX) || !isFinite(gradientY)) {
          // 그라데이션 생성 실패 시 단색 사용
          ctx.fillStyle = cluster.color
        } else {
          const gradient = ctx.createRadialGradient(
            gradientX, gradientY, 0,
            screenPos.x, screenPos.y, hoverRadius
          )
          
          // 미니멀하고 자연스러운 그라데이션
          const brightColor = this.lightenColor(cluster.color, 0.2)
          const darkColor = this.darkenColor(cluster.color, 0.15)
          
          gradient.addColorStop(0, brightColor)
          gradient.addColorStop(0.6, cluster.color)
          gradient.addColorStop(1, darkColor)
          
          ctx.fillStyle = gradient
        }
        ctx.fill()
        
        // 그림자 초기화
        ctx.shadowBlur = 0
        ctx.shadowOffsetX = 0
        ctx.shadowOffsetY = 0
        
        // 현대적이고 미니멀한 테두리
        if (isClickedPoint) {
          // 클릭된 점은 흰색 테두리
          ctx.strokeStyle = '#ffffff'
          ctx.lineWidth = 2
          ctx.stroke()
          
          // 추가 흰색 테두리
          ctx.beginPath()
          ctx.arc(screenPos.x, screenPos.y, hoverRadius + 1, 0, 2 * Math.PI)
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)'
          ctx.lineWidth = 1
          ctx.stroke()
        } else if (this.hoveredPoint === point) {
          // 호버 시 부드러운 글로우 효과
          ctx.strokeStyle = '#64b5f6'
          ctx.lineWidth = 1.5
          ctx.stroke()
          
          // 외부 글로우 링
          ctx.beginPath()
          ctx.arc(screenPos.x, screenPos.y, hoverRadius + 3, 0, 2 * Math.PI)
          ctx.strokeStyle = 'rgba(100, 181, 246, 0.2)'
          ctx.lineWidth = 2
          ctx.stroke()
        } else {
          // 일반 상태의 미세한 테두리 (모든 클러스터 동일)
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)'
          ctx.lineWidth = 0.5
          ctx.stroke()
        }
        

      })

      // 클러스터 경계선 그리기 (필터링된 포인트들만 사용)
      if (this.showClusterBorders) {
        this.renderClusterBorders(visiblePoints)
      }
    },

    renderClusterBorders(visiblePoints) {
      const ctx = this.ctx
      
      // 클러스터별로 포인트들을 그룹화
      const clusterGroups = {}
      visiblePoints.forEach(point => {
        if (!clusterGroups[point.cluster]) {
          clusterGroups[point.cluster] = []
        }
        
        const screenPos = this.worldToScreen(point.umapX, point.umapY)
        if (screenPos) {
          clusterGroups[point.cluster].push({
            x: screenPos.x,
            y: screenPos.y,
            originalPoint: point
          })
        }
      })
      
      // 클러스터별 포인트 수 체크
      const clusterSummary = Object.fromEntries(
        Object.entries(clusterGroups).map(([id, points]) => [id, points.length])
      )
      console.log('클러스터 경계선:', {
        totalClusters: Object.keys(clusterGroups).length,
        pointsPerCluster: clusterSummary,
        visiblePointsTotal: visiblePoints.length
      })
      
      // 각 클러스터의 경계선 그리기
      let successCount = 0
      Object.entries(clusterGroups).forEach(([clusterId, points]) => {
        if (points.length < 3) {
          return // 최소 3개 점이 있어야 경계선 그리기 가능
        }
        
        const cluster = this.clusters[clusterId]
        if (!cluster) {
          console.warn(`클러스터 ${clusterId}: 클러스터 정보 없음`)
          return
        }
        
        // Convex Hull 계산 (간단한 구현)
        const hull = this.calculateConvexHull(points)
        if (hull.length < 3) {
          return
        }
        
        // 경계선 그리기
        ctx.save()
        ctx.beginPath()
        ctx.moveTo(hull[0].x, hull[0].y)
        for (let i = 1; i < hull.length; i++) {
          ctx.lineTo(hull[i].x, hull[i].y)
        }
        ctx.closePath()
        
        // 반투명 채우기
        ctx.fillStyle = cluster.color + '15' // 매우 투명하게
        ctx.fill()
        
        // 경계선 스타일
        ctx.strokeStyle = cluster.color + '80' // 반투명
        ctx.lineWidth = 2
        ctx.setLineDash([5, 5]) // 점선
        ctx.stroke()
        
        // 점선 초기화
        ctx.setLineDash([])
        
        ctx.restore()
        successCount++
      })
      
      if (successCount > 0) {
        console.log(`✅ 클러스터 경계선 렌더링 완료: ${successCount}/${Object.keys(clusterGroups).length}개 클러스터`)
      } else {
        console.warn('⚠️ 경계선을 그릴 수 있는 클러스터가 없습니다 (각 클러스터마다 최소 3개 포인트 필요)')
      }
    },

    // 간단한 Convex Hull 알고리즘 (Graham Scan의 단순화 버전)
    calculateConvexHull(points) {
      if (points.length < 3) return points
      
      // 가장 아래쪽 점 찾기 (y가 가장 큰 점)
      let bottom = points[0]
      for (let i = 1; i < points.length; i++) {
        if (points[i].y > bottom.y || (points[i].y === bottom.y && points[i].x < bottom.x)) {
          bottom = points[i]
        }
      }
      
      // 각도에 따라 정렬
      const sortedPoints = points.filter(p => p !== bottom).sort((a, b) => {
        const angleA = Math.atan2(a.y - bottom.y, a.x - bottom.x)
        const angleB = Math.atan2(b.y - bottom.y, b.x - bottom.x)
        return angleA - angleB
      })
      
      // Convex Hull 계산
      const hull = [bottom]
      for (const point of sortedPoints) {
        while (hull.length > 1 && this.crossProduct(hull[hull.length-2], hull[hull.length-1], point) <= 0) {
          hull.pop()
        }
        hull.push(point)
      }
      
      return hull
    },

    crossProduct(O, A, B) {
      return (A.x - O.x) * (B.y - O.y) - (A.y - O.y) * (B.x - O.x)
    },
    
    darkenColor(color, factor) {
      const hex = color.replace('#', '')
      const r = Math.max(0, parseInt(hex.substr(0, 2), 16) * (1 - factor))
      const g = Math.max(0, parseInt(hex.substr(2, 2), 16) * (1 - factor))
      const b = Math.max(0, parseInt(hex.substr(4, 2), 16) * (1 - factor))
      return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`
    },

    lightenColor(color, factor) {
      const hex = color.replace('#', '')
      const r = Math.min(255, parseInt(hex.substr(0, 2), 16) + (255 - parseInt(hex.substr(0, 2), 16)) * factor)
      const g = Math.min(255, parseInt(hex.substr(2, 2), 16) + (255 - parseInt(hex.substr(2, 2), 16)) * factor)
      const b = Math.min(255, parseInt(hex.substr(4, 2), 16) + (255 - parseInt(hex.substr(4, 2), 16)) * factor)
      return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`
    },
    
    worldToScreen(worldX, worldY) {
      return {
        x: (worldX * this.viewport.scale) + this.viewport.x,
        y: (worldY * this.viewport.scale) + this.viewport.y
      }
    },
    
    screenToWorld(screenX, screenY) {
      return {
        x: (screenX - this.viewport.x) / this.viewport.scale,
        y: (screenY - this.viewport.y) / this.viewport.scale
      }
    },
    
    onMouseDown(event) {
      this.isDragging = true
      this.lastMousePos = { x: event.clientX, y: event.clientY }
      // 드래그 중에는 커서를 grabbing으로 변경
      this.canvas.style.cursor = 'grabbing'
    },
    
    onMouseMove(event) {
      if (this.isDragging) {
        const deltaX = event.clientX - this.lastMousePos.x
        const deltaY = event.clientY - this.lastMousePos.y
        
        this.viewport.x += deltaX
        this.viewport.y += deltaY
        
        this.lastMousePos = { x: event.clientX, y: event.clientY }
        this.needsRedraw = true
        this.requestRender()
      }
      
      // 호버 효과
      const rect = this.canvas.getBoundingClientRect()
      const mouseX = event.clientX - rect.left
      const mouseY = event.clientY - rect.top
      
      const previousHoveredPoint = this.hoveredPoint
      this.hoveredPoint = this.findPointAt(mouseX, mouseY)
      
      // 마우스 커서 스타일 변경 (드래그 중이 아닐 때만)
      if (!this.isDragging) {
        if (this.hoveredPoint) {
          this.canvas.style.cursor = 'pointer'
        } else {
          this.canvas.style.cursor = 'grab'
        }
      }
      
      // 호버 상태가 변경되었을 때만 다시 그리기
      if (previousHoveredPoint !== this.hoveredPoint) {
        this.needsRedraw = true
        this.requestRender()
      }
      
      // 호버 툴팁 업데이트
      this.updateHoverTooltip(event)
    },
    
    onMouseUp() {
      this.isDragging = false
      // 드래그 종료 후 현재 호버 상태에 맞는 커서로 복원
      this.canvas.style.cursor = this.hoveredPoint ? 'pointer' : 'grab'
    },
    
    onMouseLeave() {
      // 마우스가 캔버스를 벗어나면 호버 상태 초기화
      this.canvas.style.cursor = 'grab'
      this.hoveredPoint = null
      this.needsRedraw = true
      this.requestRender()
      
      // 호버 툴팁 숨기기
      this.hideHoverTooltip()
    },

    onWheel(event) {
      event.preventDefault()
      
      // 부드럽고 정확한 줌 팩터
      const zoomFactor = event.deltaY > 0 ? 0.9 : 1.1
      const rect = this.canvas.getBoundingClientRect()
      const mouseX = event.clientX - rect.left
      const mouseY = event.clientY - rect.top
      
      // 줌 전 상태 저장
      const oldScale = this.viewport.scale
      const oldViewportX = this.viewport.x
      const oldViewportY = this.viewport.y
      
      // 줌 전 마우스 위치의 월드 좌표 계산
      const worldX = (mouseX - oldViewportX) / oldScale
      const worldY = (mouseY - oldViewportY) / oldScale
      
      // 새로운 스케일 계산 및 제한 (동적 범위)
      this.viewport.scale = oldScale * zoomFactor
      
      // fitViewport에서 계산된 최적 스케일을 기준으로 동적 범위 설정
      const baseScale = this.getOptimalScale()
      const minScale = Math.max(0.01, baseScale * 0.1)  // 최적 스케일의 10%까지 줌아웃 
      // 최대 줌 제한 제거 - 무제한 확대 가능
      
      const requestedScale = this.viewport.scale
      this.viewport.scale = Math.max(minScale, this.viewport.scale) // 최소 제한만 적용
      
      // 마우스 위치가 고정되도록 뷰포트 위치 재계산
      this.viewport.x = mouseX - worldX * this.viewport.scale
      this.viewport.y = mouseY - worldY * this.viewport.scale
      
      // 디버깅 정보 (범위 제한이 적용되었는지 확인)
      if (requestedScale !== this.viewport.scale) {
        console.log('줌 범위 제한:', {
          요청스케일: requestedScale,
          적용스케일: this.viewport.scale,
          기준스케일: baseScale,
          최소스케일: minScale,
          최대스케일: '무제한'
        })
      }
      
      this.needsRedraw = true
      this.requestRender()
    },

    onDoubleClick(event) {
      // 더블클릭 시 줌 리셋
      event.preventDefault()
      this.resetView()
    },

    onAuxClick(event) {
      // 휠 버튼 클릭 시 줌 리셋
      if (event.button === 1) { // 휠 버튼 (중간 버튼)
        event.preventDefault()
        this.resetView()
      }
    },
    
    onClick(event) {
      // 더블클릭과 구분하기 위해 약간의 지연 추가
      if (this.clickTimeout) {
        clearTimeout(this.clickTimeout)
        this.clickTimeout = null
        return
      }
      
      this.clickTimeout = setTimeout(() => {
        if (this.hoveredPoint) {
          const rect = this.canvas.getBoundingClientRect()
          let x = event.clientX - rect.left
          let y = event.clientY - rect.top
          
          // 기존에 같은 점의 툴팁이 있는지 확인
          const existingTooltipIndex = this.activeTooltips.findIndex(
            tooltip => tooltip.point.title === this.hoveredPoint.title && 
                      tooltip.point.artist === this.hoveredPoint.artist
          )
          
          if (existingTooltipIndex !== -1) {
            // 이미 있으면 제거
            this.activeTooltips.splice(existingTooltipIndex, 1)
          } else {
            // 새로운 툴팁 추가
            const tooltipWidth = 320 // 최대 너비
            const tooltipHeight = 180 // 예상 높이
            
            // 화면 경계 조정
            if (x + tooltipWidth/2 > rect.width) {
              x = rect.width - tooltipWidth/2 - 10
            }
            if (x - tooltipWidth/2 < 0) {
              x = tooltipWidth/2 + 10
            }
            if (y - tooltipHeight < 10) {
              y = y + tooltipHeight + 20 // 아래쪽에 표시
            }
            
            // 기존 툴팁과 겹치지 않도록 위치 조정
            let adjustedX = x
            let adjustedY = y
            const overlap = this.activeTooltips.some(tooltip => {
              const distance = Math.sqrt(
                Math.pow(tooltip.position.x - adjustedX, 2) + 
                Math.pow(tooltip.position.y - adjustedY, 2)
              )
              return distance < tooltipWidth * 0.8
            })
            
            if (overlap) {
              adjustedX += tooltipWidth * 0.6
              if (adjustedX + tooltipWidth/2 > rect.width) {
                adjustedX = x - tooltipWidth * 0.6
              }
            }
            
            this.activeTooltips.push({
              id: ++this.tooltipIdCounter,
              point: this.hoveredPoint,
              worldPosition: { x: this.hoveredPoint.umapX, y: this.hoveredPoint.umapY }, // 월드 좌표 저장
              position: { x: adjustedX, y: adjustedY }, // 화면 좌표 (실시간 업데이트됨)
              isDraggedManually: false // 수동 드래그 여부
            })
            // 새 툴팁 페이지 초기화
            this.setTooltipPage(this.tooltipIdCounter, 0)
            
            this.$emit('point-selected', this.hoveredPoint)
          }
        }
        this.clickTimeout = null
      }, 200)
    },
    
    findPointAt(screenX, screenY) {
      const worldPos = this.screenToWorld(screenX, screenY)
      
      // 조정된 포인트 또는 원본 포인트 사용
      const pointsToSearch = this.adjustClusterPositions ? this.adjustedPoints : this.dataPoints
      
      for (const point of pointsToSearch) {
        // 선택된 클러스터 필터링 (선택된 클러스터가 있을 때만)  
        if (this.selectedClusters.length > 0 && !this.selectedClusters.includes(String(point.cluster))) {
          continue
        }
        
        // 연도 범위 필터링 (year가 null이면 yearOriginal에서 파싱하여 적용)
        {
          const ny = this.getNumericYear(point)
          if (ny !== null && (ny < this.yearRange[0] || ny > this.yearRange[1])) {
            continue
          }
        }
        
        // 선택된 작가 필터링 (선택된 작가가 있을 때만)
        if (this.selectedArtists.length > 0 && !this.selectedArtists.includes(point.artist)) {
          continue
        }
        
        // 검색 쿼리 필터링
        if (this.searchQuery && this.searchQuery.trim()) {
          const searchText = this.searchQuery.toLowerCase().trim()
          const artistMatch = (point.artist || '').toLowerCase().includes(searchText)
          const titleMatch = (point.title || '').toLowerCase().includes(searchText)
          
          if (!artistMatch && !titleMatch) {
            continue
          }
        }
        
        const distance = Math.sqrt(
          (point.umapX - worldPos.x) ** 2 + 
          (point.umapY - worldPos.y) ** 2
        )
        
        const threshold = 0.15 // 모든 점 동일한 클릭 감지 범위
        if (distance < threshold) {
          return point
        }
      }
      
      return null
    },

    closeTooltip(tooltipId) {
      if (tooltipId) {
        // 특정 툴팁만 제거
        const index = this.activeTooltips.findIndex(tooltip => tooltip.id === tooltipId)
        if (index !== -1) {
          this.activeTooltips.splice(index, 1)
        }
      } else {
        // 모든 툴팁 제거
        this.activeTooltips = []
      }
    },

    closeAllTooltips() {
      // 모든 툴팁을 한번에 닫기
      this.closeTooltip()
      console.log('모든 툴팁 닫기: ', this.activeTooltips.length, '개 툴팁이 닫혔습니다.')
    },

    updateHoverTooltip(event) {
      // 드래그 중이면 호버 툴팁을 숨김
      if (this.isDragging) {
        this.hideHoverTooltip()
        return
      }
      
      // 호버 툴팁 업데이트
      if (this.hoveredPoint) {
        const rect = this.canvas.getBoundingClientRect()
        const mouseX = event.clientX - rect.left
        const mouseY = event.clientY - rect.top
        
        // 툴팁 위치 계산 (마우스 위에 표시)
        const tooltipWidth = 280
        const tooltipHeight = 120
        
        let x = mouseX + 15  // 마우스 오른쪽에 표시
        let y = mouseY - tooltipHeight - 10  // 마우스 위쪽에 표시
        
        // 화면 경계 조정
        const containerRect = this.$refs.canvasContainer.getBoundingClientRect()
        if (x + tooltipWidth > containerRect.width) {
          x = mouseX - tooltipWidth - 15  // 마우스 왼쪽으로 이동
        }
        if (y < 0) {
          y = mouseY + 15  // 마우스 아래쪽으로 이동
        }
        
        // 툴팁 표시
        this.hoverTooltip = {
          visible: true,
          point: this.hoveredPoint,
          position: { x, y }
        }
      } else {
        this.hideHoverTooltip()
      }
    },

    hideHoverTooltip() {
      // 호버 툴팁 숨기기
      this.hoverTooltip = {
        visible: false,
        point: null,
        position: { x: 0, y: 0 }
      }
    },

    onDocumentClick(event) {
      // 캔버스 외부 클릭 시 모든 툴팁 닫기
      if (this.activeTooltips.length > 0 && !this.$refs.canvasContainer.contains(event.target)) {
        // 툴팁 카드 자체를 클릭한 경우는 제외
        const isTooltipClick = event.target.closest('.artwork-tooltip')
        if (!isTooltipClick) {
          this.closeTooltip() // 모든 툴팁 제거
        }
      }
    },
    
    updateTooltipPositions() {
      // 모든 활성 툴팁의 위치를 현재 뷰포트에 맞게 업데이트
      this.activeTooltips.forEach(tooltip => {
        // 드래그 중인 툴팁은 업데이트하지 않음
        if (this.tooltipDragging.isDragging && this.tooltipDragging.tooltipId === tooltip.id) {
          return
        }
        
        // 수동으로 드래그된 툴팁은 자동 위치 업데이트 제외
        if (tooltip.isDraggedManually) {
          return
        }
        
        const screenPos = this.worldToScreen(tooltip.worldPosition.x, tooltip.worldPosition.y)
        
        // 툴팁이 화면을 벗어나지 않도록 조정
        const tooltipWidth = 320
        const tooltipHeight = 180
        const containerRect = this.$refs.canvasContainer.getBoundingClientRect()
        
        let x = screenPos.x + 15  // 기본 오프셋
        let y = screenPos.y - 15
        
        // 화면 경계 조정
        if (x + tooltipWidth/2 > containerRect.width) {
          x = screenPos.x - 30  // 왼쪽으로 이동
        }
        if (y < tooltipHeight/2) {
          y = screenPos.y + 30  // 아래쪽으로 이동
        }
        
        // 위치 업데이트
        tooltip.position.x = x
        tooltip.position.y = y
      })
    },
    
    // 툴팁 드래그 기능 메서드들
    startTooltipDrag(event, tooltipId) {
      // 마우스 오른쪽 버튼은 무시
      if (event.button !== 0) return
      
      event.preventDefault()
      event.stopPropagation()
      
      const tooltip = this.activeTooltips.find(t => t.id === tooltipId)
      if (!tooltip) return
      
      this.tooltipDragging = {
        isDragging: true,
        tooltipId: tooltipId,
        startPos: { x: event.clientX, y: event.clientY },
        initialTooltipPos: { x: tooltip.position.x, y: tooltip.position.y }
      }
      
      // 전역 이벤트 리스너 추가
      document.addEventListener('mousemove', this.onTooltipDrag)
      document.addEventListener('mouseup', this.endTooltipDrag)
      
      // 드래그 중일 때 텍스트 선택 방지
      document.body.style.userSelect = 'none'
      document.body.style.cursor = 'grabbing'
    },
    
    onTooltipDrag(event) {
      if (!this.tooltipDragging.isDragging) return
      
      const tooltip = this.activeTooltips.find(t => t.id === this.tooltipDragging.tooltipId)
      if (!tooltip) return
      
      // 마우스 이동 거리 계산
      const deltaX = event.clientX - this.tooltipDragging.startPos.x
      const deltaY = event.clientY - this.tooltipDragging.startPos.y
      
      // 새로운 툴팁 위치 계산
      let newX = this.tooltipDragging.initialTooltipPos.x + deltaX
      let newY = this.tooltipDragging.initialTooltipPos.y + deltaY
      
      // 화면 경계 제한
      const containerRect = this.$refs.canvasContainer.getBoundingClientRect()
      const tooltipWidth = 320
      const tooltipHeight = 180
      
      newX = Math.max(tooltipWidth/2, Math.min(newX, containerRect.width - tooltipWidth/2))
      newY = Math.max(0, Math.min(newY, containerRect.height - tooltipHeight))
      
      // 툴팁 위치 업데이트
      tooltip.position.x = newX
      tooltip.position.y = newY
    },
    
    endTooltipDrag() {
      if (!this.tooltipDragging.isDragging) return
      
      // 드래그된 툴팁을 수동 조정됨으로 표시
      const tooltip = this.activeTooltips.find(t => t.id === this.tooltipDragging.tooltipId)
      if (tooltip) {
        tooltip.isDraggedManually = true
      }
      
      // 드래그 상태 초기화
      this.tooltipDragging = {
        isDragging: false,
        tooltipId: null,
        startPos: { x: 0, y: 0 },
        initialTooltipPos: { x: 0, y: 0 }
      }
      
      // 전역 이벤트 리스너 제거
      document.removeEventListener('mousemove', this.onTooltipDrag)
      document.removeEventListener('mouseup', this.endTooltipDrag)
      
      // 스타일 복원
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    },
    
    resetTooltipPosition(tooltipId) {
      // 툴팁을 다시 자동 추적 모드로 변경
      const tooltip = this.activeTooltips.find(t => t.id === tooltipId)
      if (tooltip) {
        tooltip.isDraggedManually = false
        
        // 즉시 위치 업데이트
        const screenPos = this.worldToScreen(tooltip.worldPosition.x, tooltip.worldPosition.y)
        const tooltipWidth = 320
        const tooltipHeight = 180
        const containerRect = this.$refs.canvasContainer.getBoundingClientRect()
        
        let x = screenPos.x + 15
        let y = screenPos.y - 15
        
        // 화면 경계 조정
        if (x + tooltipWidth/2 > containerRect.width) {
          x = screenPos.x - 30
        }
        if (y < tooltipHeight/2) {
          y = screenPos.y + 30
        }
        
        tooltip.position.x = x
        tooltip.position.y = y
      }
    },
    
    updateTooltipWorldPositions() {
      // 클러스터 조정 후 툴팁의 월드 좌표를 업데이트
      this.activeTooltips.forEach(tooltip => {
        const pointsToUse = this.adjustClusterPositions ? this.adjustedPoints : this.dataPoints
        
        // 같은 작품을 찾아서 새로운 월드 좌표로 업데이트
        const updatedPoint = pointsToUse.find(p => 
          p.title === tooltip.point.title && 
          p.artist === tooltip.point.artist &&
          p.cluster === tooltip.point.cluster
        )
        
        if (updatedPoint) {
          tooltip.worldPosition.x = updatedPoint.umapX
          tooltip.worldPosition.y = updatedPoint.umapY
          // point 정보도 업데이트
          tooltip.point = updatedPoint
          
          // 클러스터 조정으로 월드 좌표가 변경되었으므로 수동 조정 해제
          if (tooltip.isDraggedManually) {
            tooltip.isDraggedManually = false
          }
        }
      })
    },

    formatGenre(genre) {
      // JSON 데이터의 장르명을 읽기 쉬운 형태로 변환
      if (!genre) return null
      
      // 언더스코어를 공백으로 변환하고 첫 글자를 대문자로
      return genre
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ')
    },
    
    onWindowResize() {
      this.resizeCanvas()
    },

    toggleClusterAdjustment() {
      console.log(`버튼 클릭: 클러스터 조정 ${this.adjustClusterPositions ? '활성화' : '비활성화'}`)
      
      // 항상 원본 데이터로부터 시작하여 일관성 보장
      this.adjustedPoints = JSON.parse(JSON.stringify(this.dataPoints))
      
      // props가 App.vue에서 업데이트되므로 여기서는 데이터 처리만
      if (this.adjustClusterPositions) {
        console.log('버튼 클릭: 클러스터 조정 시작')
        this.performClusterAdjustment()
        console.log('버튼 클릭: 클러스터 조정 완료')
      }
      // else: 원래 위치 그대로 유지 (위에서 이미 원본으로 복원함)
      
      // 툴팁의 월드 좌표 업데이트
      this.updateTooltipWorldPositions()
      
      // 애니메이션 시스템 재초기화
      this.initBreathingSeeds()
      this.createEnergyParticles()
      
      this.fitViewport() // 뷰포트 자동 조정
      this.needsRedraw = true
      this.requestRender()
    },

    async takeScreenshot() {
      // App.vue로 이벤트 전달 (전체 페이지 스크린샷)
      this.$emit('take-full-screenshot')
    },
    
    performClusterAdjustment() {
      // 클러스터별로 그룹화
      const clusterGroups = {}
      this.adjustedPoints.forEach(point => {
        if (!clusterGroups[point.cluster]) {
          clusterGroups[point.cluster] = []
        }
        clusterGroups[point.cluster].push(point)
      })
      
            // Cluster 0 (Outliers)을 그룹으로 다른 클러스터들에 가깝게 이동
      const outlierGroup = clusterGroups['0']
      const otherGroups = Object.keys(clusterGroups).filter(id => id !== '0').map(id => clusterGroups[id])
      
      if (outlierGroup && otherGroups.length > 0) {
        // 다른 클러스터들의 전체 중심점 계산
        const allOtherPoints = otherGroups.flat()
        const otherCenterX = allOtherPoints.reduce((sum, p) => sum + p.umapX, 0) / allOtherPoints.length
        const otherCenterY = allOtherPoints.reduce((sum, p) => sum + p.umapY, 0) / allOtherPoints.length
        
        // Cluster 0의 현재 중심점 계산
        const outlierCenterX = outlierGroup.reduce((sum, p) => sum + p.umapX, 0) / outlierGroup.length
        const outlierCenterY = outlierGroup.reduce((sum, p) => sum + p.umapY, 0) / outlierGroup.length
        
        // Cluster 0 전체를 다른 클러스터들 방향으로 그룹 이동 (상대적 위치 유지)
        const moveRatio = 0.8 // 적절한 거리로 이동
        const moveX = (otherCenterX - outlierCenterX) * moveRatio
        const moveY = (otherCenterY - outlierCenterY) * moveRatio
        
        // Cluster 0의 모든 포인트를 동일하게 이동 (상대적 위치 관계 유지)
        outlierGroup.forEach(point => {
          point.umapX += moveX
          point.umapY += moveY
        })
        
        console.log(`Cluster 0을 그룹으로 (${moveX.toFixed(2)}, ${moveY.toFixed(2)})만큼 이동 (${outlierGroup.length}개 포인트)`)
      }
      
      // 각 클러스터의 중심점과 반경 계산 (트랜스제닉 이동 후)
      const clusterCenters = {}
      const clusterRadii = {}
      
      Object.keys(clusterGroups).forEach(clusterId => {
        const points = clusterGroups[clusterId]
        const xCoords = points.map(p => p.umapX)
        const yCoords = points.map(p => p.umapY)
        
        const centerX = xCoords.reduce((sum, x) => sum + x, 0) / xCoords.length
        const centerY = yCoords.reduce((sum, y) => sum + y, 0) / yCoords.length
        
        // 클러스터 반경 계산 (중심에서 가장 먼 점까지의 거리)
        const maxDistance = Math.max(...points.map(p => 
          Math.sqrt((p.umapX - centerX) ** 2 + (p.umapY - centerY) ** 2)
        ))
        
        clusterCenters[clusterId] = { x: centerX, y: centerY }
        clusterRadii[clusterId] = Math.max(maxDistance, 0.5) // 최소 반경 보장
      })
      
      // Cluster 0 전용 겹침 해결 알고리즘 (다른 클러스터들은 고정)
      const clusterIds = Object.keys(clusterCenters).sort((a, b) => parseInt(a) - parseInt(b))
      const minSeparation = 1.5
      
      // Cluster 0과 다른 클러스터들의 겹침만 해결 (다른 클러스터들은 움직이지 않음)
      for (let iteration = 0; iteration < 5; iteration++) {
        let hasAdjustment = false
        
        // Cluster 0과 각 클러스터의 겹침 확인
        for (const otherId of clusterIds) {
          if (otherId === '0') continue // 자기 자신은 제외
          
          const cluster0Center = clusterCenters['0']
          const otherCenter = clusterCenters[otherId]
          const cluster0Radius = clusterRadii['0']
          const otherRadius = clusterRadii[otherId]
          
          const distance = Math.sqrt(
            (otherCenter.x - cluster0Center.x) ** 2 + 
            (otherCenter.y - cluster0Center.y) ** 2
          )
          
          const requiredDistance = cluster0Radius + otherRadius + minSeparation
          
          // 겹치는 경우 Cluster 0만 이동
          if (distance < requiredDistance) {
            const overlap = requiredDistance - distance
            const angle = Math.atan2(cluster0Center.y - otherCenter.y, cluster0Center.x - otherCenter.x)
            
            // Cluster 0을 다른 클러스터로부터 멀어지는 방향으로 이동
            const moveX = Math.cos(angle) * overlap
            const moveY = Math.sin(angle) * overlap
            
            // Cluster 0의 모든 포인트만 이동 (다른 클러스터는 고정)
            clusterGroups['0'].forEach(point => {
              point.umapX += moveX
              point.umapY += moveY
            })
            
            // Cluster 0의 중심점만 업데이트
            clusterCenters['0'].x += moveX
            clusterCenters['0'].y += moveY
            
            hasAdjustment = true
            
            console.log(`Cluster 0을 클러스터 ${otherId}로부터 (${moveX.toFixed(2)}, ${moveY.toFixed(2)})만큼 분리`)
          }
        }
        
        // 더 이상 조정이 없으면 반복 종료
        if (!hasAdjustment) break
      }
      
      // 기존 클러스터들은 완전히 고정 (절대 움직이지 않음)
      // 원본 위치 유지를 위해 기존 클러스터들 간의 겹침 해결 로직 비활성화
      console.log('기존 클러스터들 위치 고정: 원본 레이아웃 유지')
      
              console.log('클러스터 위치 조정 완료:', Object.keys(clusterGroups).length + '개 클러스터 (Cluster 0 특별 조정 포함)')
    },

    formatFeatureValue(value) {
      // 영어 피처 값을 읽기 쉬운 형태로 변환
      if (!value || value === 'null' || value === 'undefined') {
        return 'N/A'
      }
      
      // 언더스코어를 공백으로 변환하고 각 단어의 첫 글자를 대문자로
      const formatted = value
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ')
      
      return formatted
    },

    renderDistanceLines() {
      // 클릭된 점이 2개 이상일 때만 거리선 표시
      if (this.activeTooltips.length < 2) return

      const ctx = this.ctx
      
      // 모든 점들의 조합에 대해 거리선 그리기
      for (let i = 0; i < this.activeTooltips.length; i++) {
        for (let j = i + 1; j < this.activeTooltips.length; j++) {
          const tooltip1 = this.activeTooltips[i]
          const tooltip2 = this.activeTooltips[j]
          
          // 두 점의 화면 좌표 계산
          const pos1 = this.worldToScreen(tooltip1.worldPosition.x, tooltip1.worldPosition.y)
          const pos2 = this.worldToScreen(tooltip2.worldPosition.x, tooltip2.worldPosition.y)
          
          // 거리 계산 (UMAP 좌표계에서)
          const distance = this.calculateDistance(
            tooltip1.worldPosition.x, tooltip1.worldPosition.y,
            tooltip2.worldPosition.x, tooltip2.worldPosition.y
          )
          
          // 거리에 따른 색상 계산
          const lineColor = this.getDistanceColor(distance)
          
          // 점선 그리기
          ctx.save()
          ctx.setLineDash([8, 6]) // 점선 패턴
          ctx.strokeStyle = lineColor
          ctx.lineWidth = 2
          ctx.globalAlpha = 0.8
          
          ctx.beginPath()
          ctx.moveTo(pos1.x, pos1.y)
          ctx.lineTo(pos2.x, pos2.y)
          ctx.stroke()
          
          // 선의 중간점 계산
          const midX = (pos1.x + pos2.x) / 2
          const midY = (pos1.y + pos2.y) / 2
          
          // 거리 텍스트 배경 그리기
          const distanceText = distance.toFixed(2)
          ctx.font = 'bold 12px Inter, system-ui, sans-serif'
          const textWidth = ctx.measureText(distanceText).width
          const padding = 6
          
          ctx.globalAlpha = 0.9
          ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'
          ctx.fillRect(
            midX - textWidth/2 - padding,
            midY - 8 - padding,
            textWidth + padding * 2,
            16 + padding * 2
          )
          
          // 거리 텍스트 그리기
          ctx.globalAlpha = 1
          ctx.fillStyle = lineColor
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(distanceText, midX, midY)
          
          ctx.restore()
        }
      }
    },

    calculateDistance(x1, y1, x2, y2) {
      // 유클리드 거리 계산
      return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    },

    getDistanceColor(distance) {
      // 거리에 따른 색상 매핑
      // 0-2: 녹색 (가까움)
      // 2-5: 노란색 (보통)
      // 5+: 빨간색 (멀음)
      
      if (distance <= 2) {
        // 가까운 거리: 밝은 녹색
        const intensity = Math.max(0.5, 1 - distance / 2)
        return `rgba(76, 175, 80, ${intensity})`
      } else if (distance <= 5) {
        // 중간 거리: 노란색
        const intensity = Math.max(0.6, 1 - (distance - 2) / 3)
        return `rgba(255, 193, 7, ${intensity})`
      } else {
        // 먼 거리: 빨간색
        const intensity = Math.min(1, 0.7 + (distance - 5) / 10)
        return `rgba(244, 67, 54, ${intensity})`
      }
    },

    // 애니메이션 시스템 초기화
    initAnimationSystem() {
      // 애니메이션 루프 시작
      this.startAnimationLoop()
    },

    startAnimationLoop() {
      const animate = () => {
        this.animationTime = Date.now()
        this.updateAnimations()
        this.needsRedraw = true
        this.requestRender()
        requestAnimationFrame(animate)
      }
      animate()
    },

    updateAnimations() {
      // 에너지 파티클 업데이트
      this.updateEnergyParticles()
    },

    // 각 포인트의 고유 숨쉬기 시드 생성 (데이터 기반 의미 부여)
    initBreathingSeeds() {
      this.breathingSeeds.clear()
      
      const pointsToUse = this.adjustClusterPositions ? this.adjustedPoints : this.dataPoints
      
      // 전체 데이터 분석을 위한 통계 계산
      const stats = this.calculateBreathingStats(pointsToUse)
      
      pointsToUse.forEach(point => {
        const pointKey = `${point.title}-${point.artist}-${point.cluster}`
        
        // 각 포인트마다 고유한 시드 생성 (클러스터별로 다른 베이스 주기)
        const clusterSeed = point.cluster * 0.3 // 클러스터별 위상차
        const pointSeed = Math.random() * Math.PI * 2 // 개별 포인트 위상차
        const frequency = 0.0003 + (point.cluster * 0.0001) // 클러스터별 다른 주기 (더 느리게)
        
        // 🧬 데이터 기반 의미있는 숨쉬기 강도 계산
        const amplitude = this.calculateMeaningfulAmplitude(point, stats)
        
        this.breathingSeeds.set(pointKey, {
          phase: clusterSeed + pointSeed,
          frequency: frequency,
          amplitude: amplitude
        })
      })
      
      console.log('🫁 숨쉬기 강도 설정 완료:', {
        totalPoints: pointsToUse.length,
        amplitudeRange: `${stats.minAmplitude.toFixed(2)} ~ ${stats.maxAmplitude.toFixed(2)}`,
        clusterInfluence: stats.clusterSizes,
        pioneerBonus: stats.pioneerThreshold
      })
    },

    // 숨쉬기 강도 계산을 위한 통계 데이터
    calculateBreathingStats(points) {
      // 클러스터별 작품 수 계산
      const clusterSizes = {}
      const artistWorkCounts = {}
      
      points.forEach(point => {
        // 클러스터 크기
        clusterSizes[point.cluster] = (clusterSizes[point.cluster] || 0) + 1
        
        // 작가별 작품 수
        artistWorkCounts[point.artist] = (artistWorkCounts[point.artist] || 0) + 1
      })
      
      // 년도 범위 계산 (바이오아트 초기 작품 판별용)
      const years = points.map(p => p.year).sort((a, b) => a - b)
      const earliestYear = years[0]
      const pioneerThreshold = earliestYear + 15 // 초기 15년을 "선구자 시대"로 정의
      
      return {
        clusterSizes,
        artistWorkCounts,
        maxClusterSize: Math.max(...Object.values(clusterSizes)),
        maxArtistWorks: Math.max(...Object.values(artistWorkCounts)),
        pioneerThreshold,
        minAmplitude: 0.15, // 최소 숨쉬기 강도
        maxAmplitude: 0.8   // 최대 숨쉬기 강도
      }
    },

    // 데이터 기반 의미있는 숨쉬기 강도 계산
    calculateMeaningfulAmplitude(point, stats) {
      let amplitudeScore = 0
      
      // 1. 📊 클러스터 영향력 (30% 가중치)
      const clusterSize = stats.clusterSizes[point.cluster] || 1
      const clusterInfluence = Math.min(clusterSize / stats.maxClusterSize, 1)
      amplitudeScore += clusterInfluence * 0.3
      
      // 2. 🎨 작가 중요도 (25% 가중치) - 다작 작가일수록 강하게
      const artistWorks = stats.artistWorkCounts[point.artist] || 1
      const artistInfluence = Math.min(artistWorks / stats.maxArtistWorks, 1)
      amplitudeScore += artistInfluence * 0.25
      
      // 3. 🕰️ 역사적 중요성 (20% 가중치) - 바이오아트 초기 작품
      const isPioneer = point.year <= stats.pioneerThreshold
      const historicalInfluence = isPioneer ? 1 : Math.max(0.3, (2023 - point.year) / (2023 - stats.pioneerThreshold))
      amplitudeScore += historicalInfluence * 0.2
      
      // 4. 🔴 특별 클러스터 보너스 (15% 가중치)
      let specialBonus = 0
      if (point.cluster === 0) {
        specialBonus = 1 // Outlier 클러스터는 매우 독특하므로 강하게
      } else if (point.cluster === 1) {
        specialBonus = 0.8 // 첫 번째 주요 클러스터
      }
      amplitudeScore += specialBonus * 0.15
      
      // 5. 🎯 선택 상태 보너스 (10% 가중치)
      const isSelected = this.activeTooltips.some(tooltip => 
        tooltip.point.title === point.title && 
        tooltip.point.artist === point.artist
      )
      if (isSelected) {
        amplitudeScore += 0.1 // 선택된 작품은 더 활발하게
      }
      
      // 최종 진폭 계산 (0.15 ~ 0.8 범위로 정규화)
      const finalAmplitude = stats.minAmplitude + (amplitudeScore * (stats.maxAmplitude - stats.minAmplitude))
      
      // 약간의 랜덤 변화 추가 (±10%)
      const randomVariation = (Math.random() - 0.5) * 0.2 * finalAmplitude
      
      return Math.max(stats.minAmplitude, Math.min(stats.maxAmplitude, finalAmplitude + randomVariation))
    },

        // 의미있는 연결 기반 에너지 파티클 생성
    createEnergyParticles() {
      this.energyParticles = []
      
      if (!this.dataPoints || this.dataPoints.length < 2) return
      
      const pointsToUse = this.adjustClusterPositions ? this.adjustedPoints : this.dataPoints
      
      // 1. 클러스터 경계 근처의 "다리" 작품들 찾기
      this.createBridgeParticles(pointsToUse)
      
      // 2. 같은 작가의 작품들 간 연결
      this.createArtistConnections(pointsToUse)
      
      // 3. 시간적으로 인접한 작품들 간 연결 (바이오아트 진화 흐름)
      this.createTemporalConnections(pointsToUse)
      
      // 4. 선택된 작품과 관련된 연결 (툴팁이 있을 때)
      this.createSelectionBasedConnections(pointsToUse)
    },

    // 클러스터 경계의 다리 역할을 하는 작품들 간의 연결
    createBridgeParticles(points) {
      const clusterGroups = {}
      
      // 클러스터별로 그룹화
      points.forEach(point => {
        if (!clusterGroups[point.cluster]) {
          clusterGroups[point.cluster] = []
        }
        clusterGroups[point.cluster].push(point)
      })
      
      // 각 클러스터에서 다른 클러스터와 가장 가까운 작품들 찾기
      Object.keys(clusterGroups).forEach(clusterId1 => {
        Object.keys(clusterGroups).forEach(clusterId2 => {
          if (clusterId1 >= clusterId2) return // 중복 방지
          
          const group1 = clusterGroups[clusterId1]
          const group2 = clusterGroups[clusterId2]
          
          // 각 클러스터에서 상대 클러스터와 가장 가까운 작품 찾기
          let minDistance = Infinity
          let bridgePoint1 = null
          let bridgePoint2 = null
          
          group1.forEach(p1 => {
            group2.forEach(p2 => {
              const distance = Math.sqrt(
                (p1.umapX - p2.umapX) ** 2 + (p1.umapY - p2.umapY) ** 2
              )
              if (distance < minDistance) {
                minDistance = distance
                bridgePoint1 = p1
                bridgePoint2 = p2
              }
            })
          })
          
          // 거리가 적당한 경우에만 연결 생성
          if (minDistance < 8 && bridgePoint1 && bridgePoint2) {
            this.energyParticles.push({
              id: `bridge-${clusterId1}-${clusterId2}`,
              type: 'bridge',
              fromPoint: bridgePoint1,
              toPoint: bridgePoint2,
              progress: Math.random(),
              speed: 0.0008 + Math.random() * 0.0004,
              opacity: 0.4 + Math.random() * 0.3,
              size: 1.5 + Math.random() * 1,
              color: 'rgba(120, 180, 255, 0.7)', // 다리 연결은 파란색
              phase: Math.random() * Math.PI * 2
            })
          }
        })
      })
    },

    // 같은 작가의 작품들 간 연결
    createArtistConnections(points) {
      const artistGroups = {}
      
      // 작가별로 그룹화
      points.forEach(point => {
        if (!artistGroups[point.artist]) {
          artistGroups[point.artist] = []
        }
        artistGroups[point.artist].push(point)
      })
      
      // 2개 이상 작품이 있는 작가들만
      Object.keys(artistGroups).forEach(artist => {
        const works = artistGroups[artist]
        if (works.length < 2) return
        
        // 같은 작가의 작품들을 시간순으로 정렬
        works.sort((a, b) => a.year - b.year)
        
        // 연속된 작품들 간에 연결 생성 (최대 3개까지)
        for (let i = 0; i < Math.min(works.length - 1, 2); i++) {
          const work1 = works[i]
          const work2 = works[i + 1]
          
          this.energyParticles.push({
            id: `artist-${artist}-${i}`,
            type: 'artist',
            fromPoint: work1,
            toPoint: work2,
            progress: Math.random(),
            speed: 0.0006 + Math.random() * 0.0003,
            opacity: 0.5 + Math.random() * 0.3,
            size: 1.2 + Math.random() * 0.8,
            color: 'rgba(255, 150, 100, 0.6)', // 작가 연결은 주황색
            phase: Math.random() * Math.PI * 2
          })
        }
      })
    },

    // 시간적으로 인접한 작품들 간 연결 (바이오아트 진화)
    createTemporalConnections(points) {
      // 년도별로 정렬
      const sortedByYear = [...points].sort((a, b) => a.year - b.year)
      
      // 5년 간격 내의 작품들 중 거리가 가까운 것들 연결
      for (let i = 0; i < sortedByYear.length - 1; i++) {
        const current = sortedByYear[i]
        const next = sortedByYear[i + 1]
        
        // 년도 차이가 5년 이내이고 거리가 가까운 경우
        if (next.year - current.year <= 5) {
          const distance = Math.sqrt(
            (current.umapX - next.umapX) ** 2 + (current.umapY - next.umapY) ** 2
          )
          
          if (distance < 6) {
            this.energyParticles.push({
              id: `temporal-${i}`,
              type: 'temporal',
              fromPoint: current,
              toPoint: next,
              progress: Math.random(),
              speed: 0.0005 + Math.random() * 0.0002,
              opacity: 0.3 + Math.random() * 0.2,
              size: 0.8 + Math.random() * 0.6,
              color: 'rgba(150, 255, 150, 0.5)', // 시간 흐름은 녹색
              phase: Math.random() * Math.PI * 2
            })
          }
        }
      }
    },

    // 선택된 작품과 관련된 연결
    createSelectionBasedConnections(points) {
      if (this.activeTooltips.length === 0) return
      
      this.activeTooltips.forEach(tooltip => {
        const selectedPoint = tooltip.point
        
        // 선택된 작품과 유사한 특성을 가진 작품들 찾기
        points.forEach(point => {
          if (point === selectedPoint) return
          
          let connectionStrength = 0
          
          // 같은 클러스터: +3
          if (point.cluster === selectedPoint.cluster) connectionStrength += 3
          
          // 같은 작가: +2
          if (point.artist === selectedPoint.artist) connectionStrength += 2
          
          // 비슷한 년도 (10년 이내): +1
          if (Math.abs(point.year - selectedPoint.year) <= 10) connectionStrength += 1
          
          // 연결 강도가 충분하고 거리가 적당한 경우
          const distance = Math.sqrt(
            (point.umapX - selectedPoint.umapX) ** 2 + 
            (point.umapY - selectedPoint.umapY) ** 2
          )
          
          if (connectionStrength >= 2 && distance < 10) {
            this.energyParticles.push({
              id: `selection-${tooltip.id}-${point.title}`,
              type: 'selection',
              fromPoint: selectedPoint,
              toPoint: point,
              progress: Math.random(),
              speed: 0.001 + Math.random() * 0.0005,
              opacity: 0.6 + Math.random() * 0.3,
              size: 1.5 + Math.random() * 1,
              color: 'rgba(255, 255, 100, 0.8)', // 선택 관련은 노란색
              phase: Math.random() * Math.PI * 2
            })
          }
        })
      })
    },

    calculateClusterCenters() {
      const centers = {}
      const clusterGroups = {}
      
      const pointsToUse = this.adjustClusterPositions ? this.adjustedPoints : this.dataPoints
      
      // 클러스터별로 포인트 그룹화
      pointsToUse.forEach(point => {
        if (!clusterGroups[point.cluster]) {
          clusterGroups[point.cluster] = []
        }
        clusterGroups[point.cluster].push(point)
      })
      
      // 각 클러스터의 중심점 계산
      Object.keys(clusterGroups).forEach(clusterId => {
        const points = clusterGroups[clusterId]
        const centerX = points.reduce((sum, p) => sum + p.umapX, 0) / points.length
        const centerY = points.reduce((sum, p) => sum + p.umapY, 0) / points.length
        
        centers[clusterId] = { x: centerX, y: centerY }
      })
      
      return centers
    },

    getEnergyParticleColor(clusterId1, clusterId2) {
      // 두 클러스터의 색상을 혼합한 에너지 색상 생성
      const color1 = this.clusters[clusterId1]?.color || '#4CAF50'
      const color2 = this.clusters[clusterId2]?.color || '#2196F3'
      
      // 색상 혼합을 통한 에너지 색상 계산
      const rgb1 = this.hexToRgb(color1)
      const rgb2 = this.hexToRgb(color2)
      
      const mixedR = Math.floor((rgb1.r + rgb2.r) / 2)
      const mixedG = Math.floor((rgb1.g + rgb2.g) / 2)
      const mixedB = Math.floor((rgb1.b + rgb2.b) / 2)
      
      return `rgba(${mixedR}, ${mixedG}, ${mixedB}, 0.6)`
    },

    hexToRgb(hex) {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
      return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
      } : { r: 100, g: 181, b: 246 } // 기본값
    },

    updateEnergyParticles() {
      // 각 파티클의 진행도 업데이트
      this.energyParticles.forEach(particle => {
        particle.progress += particle.speed
        
        // 파티클이 목적지에 도달하면 다시 시작
        if (particle.progress >= 1) {
          particle.progress = 0
          particle.opacity = 0.3 + Math.random() * 0.4 // 랜덤 불투명도 재설정
        }
      })
    },

    // 에너지 흐름 렌더링
    renderEnergyFlow() {
      if (this.energyParticles.length === 0) return
      
      const ctx = this.ctx
      
      ctx.save()
      
      this.energyParticles.forEach(particle => {
        if (!particle.fromPoint || !particle.toPoint) return
        
        const fromPoint = particle.fromPoint
        const toPoint = particle.toPoint
        
        // 베지어 곡선을 따라 이동하는 파티클 위치 계산
        const controlPointOffset = 1.5 // 곡선의 곡률 (더 자연스럽게)
        const midX = (fromPoint.umapX + toPoint.umapX) / 2
        const midY = (fromPoint.umapY + toPoint.umapY) / 2
        
        // 수직 방향으로 컨트롤 포인트 오프셋
        const angle = Math.atan2(toPoint.umapY - fromPoint.umapY, toPoint.umapX - fromPoint.umapX)
        const controlX = midX + Math.sin(angle) * controlPointOffset
        const controlY = midY - Math.cos(angle) * controlPointOffset
        
        // 베지어 곡선상의 현재 위치 계산
        const t = particle.progress
        const x = Math.pow(1-t, 2) * fromPoint.umapX + 2*(1-t)*t * controlX + Math.pow(t, 2) * toPoint.umapX
        const y = Math.pow(1-t, 2) * fromPoint.umapY + 2*(1-t)*t * controlY + Math.pow(t, 2) * toPoint.umapY
        
        // 화면 좌표로 변환
        const screenPos = this.worldToScreen(x, y)
        
        // 부드러운 깜빡임 효과
        const flickerIntensity = Math.sin(this.animationTime * 0.003 + particle.phase) * 0.2 + 0.8
        const currentOpacity = particle.opacity * flickerIntensity
        
        // 연결 타입별 시각적 차별화
        let glowRadius = particle.size * 3
        let coreIntensity = 1.5
        
        if (particle.type === 'selection') {
          glowRadius = particle.size * 4 // 선택된 연결은 더 큰 글로우
          coreIntensity = 2 // 더 밝은 중심
        } else if (particle.type === 'bridge') {
          glowRadius = particle.size * 3.5 // 다리 연결은 중간 글로우
        }
        
        // 파티클 렌더링
        ctx.globalAlpha = currentOpacity
        ctx.beginPath()
        ctx.arc(screenPos.x, screenPos.y, particle.size, 0, 2 * Math.PI)
        
        // 글로우 효과
        const gradient = ctx.createRadialGradient(
          screenPos.x, screenPos.y, 0,
          screenPos.x, screenPos.y, glowRadius
        )
        gradient.addColorStop(0, particle.color)
        gradient.addColorStop(1, particle.color.replace(/[\d.]+\)$/g, '0)')) // 투명도만 0으로
        
        ctx.fillStyle = gradient
        ctx.fill()
        
        // 중심 밝은 점 (연결 타입별 다른 강도)
        ctx.globalAlpha = currentOpacity * coreIntensity
        ctx.fillStyle = '#ffffff'
        ctx.beginPath()
        ctx.arc(screenPos.x, screenPos.y, particle.size * 0.2, 0, 2 * Math.PI)
        ctx.fill()
      })
      
      ctx.restore()
    }
  }
}
</script>

<style scoped>
.umap-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  background: #121212;
  overflow: hidden;
}

.umap-container {
  width: 100%;
  height: 100%;
  position: relative;
}



.main-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

/* 툴팁 스타일 */
.artwork-tooltip {
  position: absolute;
  z-index: 1000;
  transform: translate(-50%, -100%);
  margin-top: -10px;
  pointer-events: auto;
  animation: fadeInTooltip 0.2s ease-out;
}

.tooltip-card {
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.4),
    0 2px 8px rgba(0, 0, 0, 0.2);
}

/* 툴팁 스크롤 영역 스타일링 */
.tooltip-card .v-card-text {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.3) transparent;
}

.tooltip-card .v-card-text::-webkit-scrollbar {
  width: 4px;
}

.tooltip-card .v-card-text::-webkit-scrollbar-track {
  background: transparent;
}

.tooltip-card .v-card-text::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
}

.tooltip-card .v-card-text::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

/* 컴팩트한 툴팁 세부 스타일 */
.tooltip-details .detail-item {
  display: flex;
  align-items: flex-start;
  line-height: 1.3;
  margin-bottom: 4px;
  padding: 2px 0;
}

.tooltip-details .detail-item:last-child {
  margin-bottom: 0;
}

.tooltip-details .detail-item span {
  word-break: break-word;
  flex-wrap: wrap;
}

.tooltip-details .detail-item span:first-child {
  min-width: 80px;
  flex-shrink: 0;
}

/* 7개 피처 구분을 위한 시각적 개선 */
.tooltip-details {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 8px;
  margin-top: 8px;
}

/* 툴팁 타이틀 텍스트 말줄임 */
.tooltip-card .text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 7개 피처 표시를 위한 컴팩트한 칩 스타일 */
.tooltip-card .v-chip {
  margin: 1px !important;
}

/* 툴팁 제목 영역 최적화 */
.tooltip-card .v-card-title {
  flex-shrink: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

/* 피처 표시 영역의 균등한 간격 */
.tooltip-details .detail-item span:first-child {
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
}

.tooltip-details .detail-item span:last-child {
  color: rgba(255, 255, 255, 0.95);
  flex: 1;
  text-align: right;
}

/* 툴팁 애니메이션 */
@keyframes fadeInTooltip {
  from {
    opacity: 0;
    transform: translate(-50%, -100%) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -100%) scale(1);
  }
}

/* 툴팁이 화면 경계를 벗어나지 않도록 조정 */
.artwork-tooltip.adjust-left {
  transform: translate(-20%, -100%);
}

.artwork-tooltip.adjust-right {
  transform: translate(-80%, -100%);
}

.artwork-tooltip.adjust-bottom {
  transform: translate(-50%, 10px);
  margin-top: 10px;
}

/* 모든 툴팁 닫기 버튼 */
.close-all-tooltips-btn {
  position: fixed !important;
  top: 20px;
  right: 340px; /* 오른쪽 사이드바 너비 + 여백 고려 */
  z-index: 2000;
  background: linear-gradient(135deg, #d32f2f, #b71c1c) !important;
  color: white !important;
  font-weight: 600 !important;
  box-shadow: 0 4px 16px rgba(211, 47, 47, 0.4) !important;
  transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1) !important;
  animation: slide-in-bounce 0.5s ease-out;
  border-radius: 8px !important;
  text-transform: none !important;
  min-width: auto !important;
  padding: 8px 16px !important;
}

.close-all-tooltips-btn:hover {
  background: linear-gradient(135deg, #f44336, #d32f2f) !important;
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 6px 20px rgba(211, 47, 47, 0.5) !important;
}

.close-all-tooltips-btn:active {
  transform: translateY(0) scale(0.98);
}

@keyframes slide-in-bounce {
  0% {
    opacity: 0;
    transform: translateX(100px) scale(0.8);
  }
  70% {
    opacity: 1;
    transform: translateX(-5px) scale(1.05);
  }
  100% {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

/* 반응형 버튼 위치 조정 */
@media (max-width: 1280px) {
  .close-all-tooltips-btn {
    right: 320px; /* 중간 화면에서 사이드바 너비 조정 */
  }
}

@media (max-width: 960px) {
  .close-all-tooltips-btn {
    right: 300px; /* 작은 화면에서 사이드바 너비 조정 */
  }
}

@media (max-width: 768px) {
  .close-all-tooltips-btn {
    top: 10px;
    right: 10px; /* 모바일에서는 사이드바가 숨겨지므로 오른쪽 끝으로 */
    font-size: 12px !important;
    padding: 6px 12px !important;
  }
}

/* 로딩 오버레이 */
.v-overlay__content {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* 다이얼로그 개선 */
.gap-2 {
  gap: 8px;
}

/* 툴팁 드래그 관련 스타일 */
.tooltip-drag-handle {
  cursor: grab;
  user-select: none;
  transition: background-color 0.2s ease;
}

.tooltip-drag-handle:hover {
  background-color: rgba(66, 66, 66, 0.8) !important;
}

.tooltip-drag-handle.dragging {
  cursor: grabbing !important;
  background-color: rgba(81, 81, 81, 0.9) !important;
}

.tooltip-drag-handle.manually-positioned {
  border-left: 3px solid #2196F3 !important;
  background-color: rgba(33, 150, 243, 0.1) !important;
}

.tooltip-drag-handle.manually-positioned:hover {
  background-color: rgba(33, 150, 243, 0.2) !important;
}

.artwork-tooltip .tooltip-card {
  transition: box-shadow 0.2s ease;
}

.artwork-tooltip:has(.tooltip-drag-handle.dragging) .tooltip-card {
  box-shadow: 0 8px 25px -5px rgba(0,0,0,0.5), 0 6px 10px -5px rgba(0,0,0,0.4) !important;
}

/* 호버 툴팁 스타일 */
.hover-tooltip {
  position: absolute;
  z-index: 1005; /* 클릭 툴팁(1000)보다 높게 */
  pointer-events: none; /* 마우스 이벤트 차단하여 호버 안정성 확보 */
  transition: opacity 0.2s ease;
}

.hover-tooltip-card {
  border: 1px solid rgba(255, 255, 255, 0.15) !important;
  backdrop-filter: blur(12px);
  background: rgba(33, 33, 33, 0.95) !important;
}

.hover-tooltip-content {
  line-height: 1.4;
}

.hover-tooltip-content .text-body-2 {
  margin-bottom: 4px;
  max-width: 240px;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.hover-tooltip-content .text-caption {
  display: flex;
  align-items: center;
  margin-bottom: 2px;
  color: rgba(255, 255, 255, 0.8) !important;
  font-size: 11px !important;
}

.hover-tooltip-content .text-caption:last-child {
  margin-bottom: 0;
}

/* 호버 툴팁 애니메이션 */
@keyframes fadeInHover {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.hover-tooltip {
  animation: fadeInHover 0.15s ease-out;
}

/* 호버 툴팁과 클릭 툴팁 구분을 위한 시각적 차이 */
.hover-tooltip-card {
  border-left: 3px solid #4CAF50 !important; /* 녹색 테두리로 구분 */
}

/* 상세 모드 클릭 툴팁 스타일 */
.tooltip-card {
  border-left: 3px solid #2196F3 !important; /* 파란색 테두리로 구분 */
}

/* 요약 모드 고정 툴팁 스타일 */
.summary-fixed-tooltip {
  border-left: 3px solid #FF9800 !important; /* 주황색 테두리로 구분 */
  background: rgba(33, 33, 33, 0.95) !important;
  backdrop-filter: blur(12px);
  animation: fadeInSummary 0.25s ease-out;
}

.summary-tooltip-content {
  line-height: 1.5;
}

.summary-tooltip-content .text-caption {
  display: flex;
  align-items: center;
  margin-bottom: 3px;
}

.summary-tooltip-content .text-caption:last-child {
  margin-bottom: 0;
}

/* 요약 툴팁 애니메이션 */
@keyframes fadeInSummary {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style> 
