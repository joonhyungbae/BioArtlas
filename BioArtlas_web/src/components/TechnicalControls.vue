<template>
  <div class="technical-controls">
    <!-- 언어 전환 -->
    <v-card class="mb-3" variant="tonal" color="grey-darken-2">
      <v-card-subtitle class="text-grey-lighten-1 font-weight-medium pb-1">
        <v-icon left size="small" class="mr-2">mdi-translate</v-icon>
        {{ $t('common.language') }}
      </v-card-subtitle>
      <v-card-text class="pt-1 pb-3">
        <v-btn-toggle
          v-model="currentLanguage"
          @update:model-value="changeLanguage"
          color="primary"
          variant="outlined"
          density="compact"
          mandatory
          class="language-toggle"
          style="width: 100%; display: flex;"
        >
          <v-btn value="en" size="small" style="flex: 1; min-width: 0;">
            {{ $t('common.english') }}
          </v-btn>
          <v-btn value="ko" size="small" style="flex: 1; min-width: 0;">
            {{ $t('common.korean') }}
          </v-btn>
        </v-btn-toggle>
      </v-card-text>
    </v-card>

    <!-- 사용 가이드 -->
    <v-card
      class="mb-3"
      variant="tonal"
      color="grey-darken-2"
    >
      <v-card-title class="d-flex align-center justify-space-between pa-3">
        <div class="d-flex align-center">
          <v-icon color="grey-lighten-1" class="mr-2">mdi-lightbulb-outline</v-icon>
          <span class="text-body-2 font-weight-medium">{{ $t('controls.usageGuide') }}</span>
        </div>
        <v-btn
          @click="toggleGuidePanel"
          icon="small"
          variant="text"
          size="small"
          color="grey-lighten-1"
        >
          <v-icon>{{ guideCollapsed ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
        </v-btn>
      </v-card-title>
      
      <v-expand-transition>
        <v-card-text v-show="!guideCollapsed" class="pa-3 pt-0">
          <v-list density="compact" class="bg-transparent guide-list">
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-drag</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('guide.drag') }}</v-list-item-title>
            </v-list-item>
            
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-magnify-plus-outline</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('guide.wheel') }}</v-list-item-title>
            </v-list-item>
            
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-cursor-move</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('guide.hover') }}</v-list-item-title>
            </v-list-item>
            
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-cursor-default-click</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('guide.click') }}</v-list-item-title>
            </v-list-item>
            
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-tooltip-text</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('guide.tooltipMode') }}</v-list-item-title>
            </v-list-item>
            
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-gesture-double-tap</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('guide.doubleClick') }}</v-list-item-title>
            </v-list-item>
            
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-mouse-scroll-wheel</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('guide.wheelButton') }}</v-list-item-title>
            </v-list-item>
            
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-border-all-variant</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('guide.borders') }}</v-list-item-title>
            </v-list-item>
            
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-ruler</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('guide.multiSelect') }}</v-list-item-title>
            </v-list-item>
            
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-camera</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('guide.screenshot') }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-expand-transition>
    </v-card>

    <!-- 시각화 통계 -->
    <v-card v-if="Object.keys(clusters).length > 0" class="mb-3" variant="tonal" color="grey-darken-2">
      <v-card-subtitle class="text-grey-lighten-1 font-weight-medium pb-1">
        <v-icon left size="small" class="mr-2">mdi-chart-pie</v-icon>
        {{ $t('controls.visualizationStats') }}
      </v-card-subtitle>
      <v-card-text class="pt-1 pb-3">
        <v-row dense>
          <v-col cols="4">
            <div class="text-center">
              <div class="text-h6 text-white font-weight-bold">{{ visibleStats.clusters }}</div>
              <div class="text-caption text-grey-lighten-1">{{ $t('controls.clusters') }}</div>
            </div>
          </v-col>
          <v-col cols="4">
            <div class="text-center">
              <div class="text-h6 text-white font-weight-bold">{{ visibleStats.artworks }}</div>
              <div class="text-caption text-grey-lighten-1">{{ $t('controls.artworks') }}</div>
            </div>
          </v-col>
          <v-col cols="4">
            <div class="text-center">
              <div class="text-h6 text-white font-weight-bold">{{ visibleStats.artists }}</div>
              <div class="text-caption text-grey-lighten-1">{{ $t('controls.artists') }}</div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- UMAP 설정 -->
    <v-card
      class="mb-3"
      variant="tonal"
      color="grey-darken-2"
    >
      <v-card-title class="d-flex align-center pa-3">
        <v-icon color="grey-lighten-1" class="mr-2">mdi-tune</v-icon>
        <span class="text-body-1 font-weight-medium">{{ $t('controls.umapSettings') }}</span>
      </v-card-title>

      <v-card-text class="pa-3 pt-0">
        <!-- UMAP/클러스터링 설정 정보 (읽기 전용, 개별 접기) -->
        <div class="umap-info mb-4">
          <div class="d-flex align-center justify-space-between text-caption text-grey-lighten-1 mb-2">
            <div class="d-flex align-center">
              <v-icon size="small" class="mr-1">mdi-information-outline</v-icon>
              <span>{{ $t('controls.currentUmapSettings') }}</span>
            </div>
            <v-btn
              @click="toggleUmapInfo"
              icon="small"
              variant="text"
              size="x-small"
              color="grey-lighten-1"
            >
              <v-icon>{{ umapInfoCollapsed ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
            </v-btn>
          </div>
          <v-expand-transition>
            <div v-show="!umapInfoCollapsed" class="umap-params pa-2 rounded" style="background: rgba(255, 255, 255, 0.05);">
              <!-- 가독성 높은 요약 -->
              <div class="text-caption text-white font-weight-medium mb-1">
                <span>Clustering:</span>
                <span class="ml-1">
                  {{ (metadata?.clustering?.algorithm || 'KMeans') }}
                  <span v-if="metadata?.clustering?.k">(k={{ metadata.clustering.k }})</span>
                </span>
              </div>
              <div class="text-caption text-grey-lighten-1 mb-2">
                <span v-if="metadata?.clustering?.space">space={{ metadata.clustering.space }}</span>
                <span v-if="metadata?.clustering?.feature_key" class="ml-2">feature={{ metadata.clustering.feature_key }}</span>
                <span v-if="metadata?.clustering?.silhouette !== undefined && metadata?.clustering?.silhouette !== null" class="ml-2">sil={{ Number(metadata.clustering.silhouette).toFixed(3) }}</span>
              </div>
              <div class="text-caption text-white font-weight-medium mb-1">
                <span>Visualization:</span>
                <span class="ml-1">
                  {{ (metadata?.viz?.method || 'UMAP') }}
                </span>
              </div>
              <div class="text-caption text-grey-lighten-1">
                <span v-if="metadata?.viz?.metric">metric={{ metadata.viz.metric }}</span>
                <span v-if="metadata?.viz?.n_neighbors !== undefined" class="ml-2">n_neighbors={{ metadata.viz.n_neighbors }}</span>
                <span v-if="metadata?.viz?.min_dist !== undefined" class="ml-2">min_dist={{ metadata.viz.min_dist }}</span>
                <span v-if="metadata?.viz?.spread !== undefined" class="ml-2">spread={{ metadata.viz.spread }}</span>
              </div>
            </div>
          </v-expand-transition>
        </div>

        <div class="control-buttons">
            <v-btn
              @click="onResetView"
              size="small"
              color="grey-lighten-1"
              variant="tonal"
              block
              class="mb-2"
              prepend-icon="mdi-refresh"
            >
              {{ $t('controls.resetView') }}
            </v-btn>
            
            
            <!--
            클러스터 위치 조정 토글 (주석 처리)
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="d-flex align-center">
                <v-icon size="small" color="grey-lighten-1" class="mr-2">mdi-vector-arrange-below</v-icon>
                <span class="text-body-2 text-white">{{ $t('controls.adjustClusterPositions') }}</span>
              </div>
              <v-switch
                :model-value="adjustClusterPositions"
                @update:model-value="onToggleAdjustment"
                color="success"
                density="compact"
                hide-details
                inset
              />
            </div>
            -->
            
            <!--
            상태 안내 텍스트 (주석 처리)
            <div class="text-caption text-grey-lighten-1 mb-3 pl-6">
              <v-icon size="x-small" class="mr-1">
                {{ adjustClusterPositions ? 'mdi-check-circle' : 'mdi-circle-outline' }}
              </v-icon>
              {{ adjustClusterPositions ? $t('controls.adjustedPositionStatus') : $t('controls.originalPositionStatus') }}
            </div>
            -->

            <!-- 클러스터 경계선 표시 토글 -->
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="d-flex align-center">
                <v-icon size="small" color="grey-lighten-1" class="mr-2">mdi-border-all-variant</v-icon>
                <span class="text-body-2 text-white">{{ $t('controls.showClusterBorders') }}</span>
              </div>
              <v-switch
                :model-value="showClusterBorders"
                @update:model-value="onToggleBorders"
                color="info"
                density="compact"
                hide-details
                inset
              />
            </div>
            
            <!-- 경계선 상태 안내 텍스트 -->
            <div class="text-caption text-grey-lighten-1 mb-3 pl-6">
              <v-icon size="x-small" class="mr-1">
                {{ showClusterBorders ? 'mdi-eye' : 'mdi-eye-off' }}
              </v-icon>
              {{ showClusterBorders ? $t('controls.bordersShownStatus') : $t('controls.bordersHiddenStatus') }}
            </div>

            <!-- 툴팁 모드 토글 -->
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="d-flex align-center">
                <v-icon size="small" color="grey-lighten-1" class="mr-2">mdi-tooltip-text</v-icon>
                <span class="text-body-2 text-white">{{ $t('controls.tooltipMode') }}</span>
              </div>
              <v-switch
                :model-value="tooltipDetailMode"
                @update:model-value="onToggleTooltipMode"
                color="primary"
                density="compact"
                hide-details
                inset
              />
            </div>
            
            <!-- 툴팁 모드 상태 안내 텍스트 -->
            <div class="text-caption text-grey-lighten-1 mb-4 pl-6">
              <v-icon size="x-small" class="mr-1">
                {{ tooltipDetailMode ? 'mdi-information' : 'mdi-information-outline' }}
              </v-icon>
              {{ tooltipDetailMode ? $t('controls.detailedModeStatus') : $t('controls.summaryModeStatus') }}
            </div>

            <!-- 현재 뷰 스크린샷 버튼 -->
            <v-btn
              @click="onTakeScreenshot"
              color="purple-darken-1"
              variant="tonal"
              block
              class="mb-2"
              prepend-icon="mdi-camera"
              :loading="screenshotLoading"
            >
              {{ $t('controls.currentViewScreenshot') }}
            </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- 크레딧 -->
    <v-card
      class="mb-3"
      variant="tonal"
      color="grey-darken-2"
    >
      <v-card-title class="d-flex align-center justify-space-between pa-3">
        <div class="d-flex align-center">
          <v-icon color="grey-lighten-1" class="mr-2">mdi-account-heart</v-icon>
          <span class="text-body-2 font-weight-medium">{{ $t('controls.credits') }}</span>
        </div>
        <v-btn
          @click="toggleCreditPanel"
          icon="small"
          variant="text"
          size="small"
          color="grey-lighten-1"
        >
          <v-icon>{{ creditCollapsed ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
        </v-btn>
      </v-card-title>
      
      <v-expand-transition>
        <v-card-text v-show="!creditCollapsed" class="pa-3 pt-0">
          <v-list density="compact" class="bg-transparent credit-list">
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-account-circle</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('credits.researcher') }}</v-list-item-title>
            </v-list-item>
            
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-lightbulb-on</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('credits.inspiration') }}</v-list-item-title>
            </v-list-item>
            
            
            <v-list-item density="compact" class="px-0">
              <template v-slot:prepend>
                <v-icon size="small" color="white">mdi-copyright</v-icon>
              </template>
              <v-list-item-title class="text-caption text-white">{{ $t('credits.copyright') }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-expand-transition>
    </v-card>


  </div>
</template>

<script>
export default {
  name: 'TechnicalControls',
  props: {
    clusters: {
      type: Object,
      default: () => ({})
    },
    selectedClusters: {
      type: Array,
      default: () => []
    },
    visibleStats: {
      type: Object,
      required: true
    },
    adjustClusterPositions: {
      type: Boolean,
      default: true
    },
    showClusterBorders: {
      type: Boolean,
      default: false
    },
    tooltipDetailMode: {
      type: Boolean,
      default: true
    },
    metadata: {
      type: Object,
      default: null
    }
  },
  emits: ['reset-view', 'toggle-adjustment', 'toggle-borders', 'toggle-tooltip-mode', 'take-screenshot'],
  data() {
    return {
      // 언어 설정
      currentLanguage: this.$i18n?.locale || 'en',
      // 패널 상태
      controlsCollapsed: false,
      umapInfoCollapsed: true,
      guideCollapsed: true,
      creditCollapsed: true,
      screenshotLoading: false
    }
  },
  computed: {
    
  },
  mounted() {
    // 저장된 언어 설정 적용 (English 우선)
    const savedLocale = localStorage.getItem('locale') || 'en'
    this.currentLanguage = savedLocale
    if (this.$i18n.locale !== savedLocale) {
      this.$i18n.locale = savedLocale
    }
  },
  methods: {
    changeLanguage(newLanguage) {
      if (newLanguage && newLanguage !== this.$i18n.locale) {
        this.$i18n.locale = newLanguage
        localStorage.setItem('locale', newLanguage)
        this.currentLanguage = newLanguage
      }
    },
    toggleControlsPanel() {
      this.controlsCollapsed = !this.controlsCollapsed
    },
    toggleUmapInfo() {
      this.umapInfoCollapsed = !this.umapInfoCollapsed
    },
    toggleGuidePanel() {
      this.guideCollapsed = !this.guideCollapsed
    },
    toggleCreditPanel() {
      this.creditCollapsed = !this.creditCollapsed
    },
    onResetView() {
      this.$emit('reset-view')
    },
    onToggleAdjustment() {
      this.$emit('toggle-adjustment')
    },
    onToggleBorders() {
      this.$emit('toggle-borders')
    },
    onToggleTooltipMode() {
      this.$emit('toggle-tooltip-mode')
    },
    async onTakeScreenshot() {
      this.screenshotLoading = true
      try {
        await this.$emit('take-screenshot')
      } catch (error) {
        console.error(this.$t('loading.screenshotGenerating'), error)
      } finally {
        // 약간의 딜레이를 두어 사용자가 로딩을 인지할 수 있도록
        setTimeout(() => {
          this.screenshotLoading = false
        }, 1000)
      }
    }
  }
}
</script>

<style scoped>
.technical-controls {
  padding: 12px;
  background: transparent;
  display: flex;
  flex-direction: column;
}

/* 컨트롤 스타일 */
.control-item {
  margin-bottom: 16px;
}

.control-buttons .v-btn {
  font-size: 0.75rem;
}

/* 언어 전환 버튼 */
.language-toggle {
  overflow: hidden !important;
}

.language-toggle .v-btn {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 가이드 목록 */
.guide-list .v-list-item {
  min-height: 32px;
}

/* 크레딧 목록 */
.credit-list .v-list-item {
  min-height: 32px;
  align-items: flex-start; /* 아이콘과 텍스트를 상단 정렬 */
  padding: 4px 0; /* 위아래 여백 조정 */
}

/* 크레딧 아이콘 정렬 */
.credit-list .v-list-item__prepend {
  align-self: flex-start;
  margin-top: 2px; /* 아이콘을 텍스트 첫 줄에 맞춤 */
}

/* 크레딧 텍스트 줄바꿈 */
.credit-list .v-list-item-title {
  white-space: normal !important;
  word-wrap: break-word;
  overflow-wrap: break-word;
  line-height: 1.4;
  padding-right: 8px;
  max-width: 100%;
}

/* 스크롤바 스타일링 */
.technical-controls::-webkit-scrollbar {
  width: 6px;
}

.technical-controls::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
}

.technical-controls::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.technical-controls::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Firefox 스크롤바 */
.technical-controls {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) rgba(255, 255, 255, 0.05);
}

/* 애니메이션 */
.v-card {
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.v-card:hover {
  transform: translateY(-1px);
}

/* 호버 효과 */
.v-btn:hover {
  transform: scale(1.02);
  transition: transform 0.2s ease;
}
</style> 