<template>
  <div class="cluster-controls">
    <div class="fixed-controls">
      <!-- 검색 -->
      <v-autocomplete
        :model-value="searchQuery"
        @update:model-value="updateSearchQuery"
        :items="searchOptions"
        item-title="title"
        item-value="value"
        :label="$t('search.searchArtistOrArtwork')"
        :placeholder="$t('search.searchPlaceholder')"
        prepend-inner-icon="mdi-magnify"
        variant="outlined"
        density="compact"
        clearable
        class="mb-4"
        color="grey-lighten-1"
        hide-details
        :custom-filter="customFilter"
      >
        <template v-slot:item="{ props, item }">
          <v-list-item v-bind="props" :title="item.title" :subtitle="item.raw.subtitle">
            <template v-slot:prepend>
              <v-icon size="small" :color="item.raw.type === 'artist' ? 'blue-lighten-1' : 'green-lighten-1'">
                {{ item.raw.type === 'artist' ? 'mdi-account' : 'mdi-palette' }}
              </v-icon>
            </template>
          </v-list-item>
        </template>
        
        <template v-slot:no-data>
          <v-list-item>
            <v-list-item-title class="text-grey-lighten-1">
              {{ $t('search.noResults') }}
            </v-list-item-title>
          </v-list-item>
        </template>
      </v-autocomplete>

      <!-- 연도 필터 -->
      <v-card class="mb-2 year-filter-card" :class="{ 'playing': isPlaying }" variant="tonal" color="grey-darken-2">
        <v-card-subtitle class="d-flex justify-space-between align-center pb-0 pt-3 year-card-header">
          <span class="text-grey-lighten-1 font-weight-medium">
            <v-icon left size="small" class="mr-2">mdi-calendar-range</v-icon>
            {{ $t('filters.yearRange') }}
          </span>
          <div class="play-button-container">
            <v-tooltip location="top">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="isPlaying ? 'mdi-stop' : 'mdi-play'"
                  size="x-small"
                  variant="flat"
                  :color="isPlaying ? 'error' : 'primary'"
                  @click="togglePlay"
                  :disabled="yearRange[0] >= yearRange[1]"
                  class="year-play-button"
                >
                </v-btn>
              </template>
              <span v-if="isPlaying">{{ $t('filters.stopPlay') }}</span>
              <span v-else>{{ $t('filters.playTimeline') }}</span>
            </v-tooltip>
          </div>
        </v-card-subtitle>
        <v-card-text class="pt-1 pb-0 px-4">
          <div class="year-slider-container">
            <v-range-slider
              v-model="yearRange"
              :min="1980"
              :max="2023"
              step="1"
              thumb-label="always"
              color="grey-lighten-1"
              track-color="grey-darken-1"
              @end="onYearRangeChange"
              class="mt-4 black-thumb-label"
              style="margin-bottom: -12px;"
              :disabled="isPlaying"
            ></v-range-slider>
          </div>
          <div class="d-flex align-center justify-center ga-2" style="margin-top: -8px; margin-bottom: 8px;">
            <v-text-field
              :model-value="yearRange[0]"
              @update:model-value="updateStartYear"
              type="number"
              :min="1980"
              :max="2023"
              density="compact"
              variant="outlined"
              hide-details
              class="year-input"
              color="grey-lighten-1"
              :disabled="isPlaying"
            ></v-text-field>
            <span class="text-grey-lighten-1 text-caption mx-1">-</span>
            <v-text-field
              :model-value="yearRange[1]"
              @update:model-value="updateEndYear"
              type="number"
              :min="1980"
              :max="2023"
              density="compact"
              variant="outlined"
              hide-details
              class="year-input"
              color="grey-lighten-1"
              :disabled="isPlaying"
            ></v-text-field>
          </div>
          
          <!-- 플레이 상태 표시 -->
          <div v-if="isPlaying" class="text-center mb-2">
            <v-chip
              size="small"
              color="error"
              variant="tonal"
              class="play-status-chip"
            >
              <v-icon left size="small">mdi-play</v-icon>
              {{ playCurrentEndYear }} {{ $t('filters.playingStatus') }} ({{ playTargetYear }} {{ $t('filters.playingTarget') }})
            </v-chip>
          </div>
        </v-card-text>
      </v-card>

      <!-- 작가 필터 -->
      <v-card class="mb-2" variant="tonal" color="grey-darken-2">
        <v-card-subtitle class="d-flex justify-space-between align-center pb-1">
          <span class="text-grey-lighten-1 font-weight-medium">
            <v-icon left size="small" class="mr-2">mdi-account-group</v-icon>
            {{ $t('filters.artistSelection') }}
          </span>
          <div class="d-flex ga-1">
            <v-btn
              size="small"
              variant="text"
              color="grey-lighten-1"
              @click="clearAllArtists"
              class="text-caption px-2"
            >
              {{ $t('filters.clearAll') }}
            </v-btn>
          </div>
        </v-card-subtitle>
        
        <v-card-text class="pt-2 pb-3 px-4 artist-card-text">
          <!-- 검색 입력 -->
          <v-autocomplete
            v-model="artistSearchQuery"
            :items="artistSearchOptions"
            item-title="name"
            item-value="name"
            :label="$t('filters.artistSearch')"
            :placeholder="$t('filters.artistSearchPlaceholder')"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            density="compact"
            clearable
            class="mb-3"
            color="grey-lighten-1"
            hide-details
            :custom-filter="artistCustomFilter"
            @update:model-value="onArtistSearchSelect"
          >
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props" :title="translateArtist(item.raw.name)" :subtitle="`${item.raw.workCount} ${$t('filters.worksCount')} • ${item.raw.yearRangeText}`">
                <template v-slot:prepend>
                  <v-icon size="small" color="blue-lighten-1">mdi-account</v-icon>
                </template>
              </v-list-item>
            </template>
            
            <template v-slot:no-data>
              <v-list-item>
                <v-list-item-title class="text-grey-lighten-1">
                  {{ $t('filters.artistSearchNoResults') }}
                </v-list-item-title>
              </v-list-item>
            </template>
          </v-autocomplete>
          
          <!-- 선택된 작가 통계 (항상 표시) -->
          <div class="mb-3 pa-2 rounded" style="background: rgba(255, 255, 255, 0.05);">
            <div class="d-flex justify-space-between text-caption">
              <span class="text-grey-lighten-1">{{ $t('filters.selectedLabel') }}:</span>
              <span class="text-white font-weight-medium">{{ selectedArtistsStats?.artistCount || 0 }}{{ $t('filters.artistsUnit') }}</span>
            </div>
            <div class="d-flex justify-space-between text-caption">
              <span class="text-grey-lighten-1">{{ $t('filters.worksLabel') }}:</span>
              <span class="text-white font-weight-medium">{{ selectedArtistsStats?.totalWorks || 0 }}{{ $t('filters.worksUnit') }}</span>
            </div>
            <div class="d-flex justify-space-between text-caption">
              <span class="text-grey-lighten-1">{{ $t('filters.clustersLabel') }}:</span>
              <span class="text-white font-weight-medium">{{ selectedArtistsStats?.clusterCount || 0 }}{{ $t('filters.clustersUnit') }}</span>
            </div>
          </div>
          
          <!-- 작가 목록 -->
          <div class="artist-list-container">
            <v-list density="compact" class="bg-transparent artist-list">
              <v-list-item
                v-for="artist in filteredArtists"
                :key="artist.name"
                class="artist-item px-1"
                @click="toggleArtist(artist.name)"
              >
                <template v-slot:prepend>
                  <v-checkbox
                    :model-value="selectedArtists.includes(artist.name)"
                    hide-details
                    color="grey-lighten-1"
                    density="compact"
                    @click.stop="toggleArtist(artist.name)"
                  />
                </template>
                
                <template v-slot:title>
                  <div class="artist-info">
                    <div class="d-flex align-center justify-space-between">
                      <span class="text-body-2 font-weight-medium text-white artist-name">
                        {{ translateArtist(artist.name) }}
                      </span>
                      <v-chip 
                        size="x-small" 
                        color="grey-lighten-1" 
                        variant="tonal"
                        class="ml-2"
                      >
                        {{ artist.workCount }}
                      </v-chip>
                    </div>
                    <div class="text-caption text-grey-lighten-1 mt-1">
                      <v-icon size="x-small" class="mr-1">mdi-calendar</v-icon>
                      {{ artist.yearRangeText }}
                      <span class="mx-2">•</span>
                      <v-icon size="x-small" class="mr-1">mdi-group</v-icon>
                      {{ artist.clusters.length }} {{ $t('filters.clustersCount') }}
                    </div>
                  </div>
                </template>
              </v-list-item>
              
              <!-- 검색 결과 없음 -->
              <v-list-item v-if="filteredArtists.length === 0" class="text-center">
                <v-list-item-title class="text-grey-lighten-1 text-caption">
                  <v-icon class="mr-2">mdi-magnify</v-icon>
                  {{ $t('filters.artistSearchNoResults') }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- 클러스터 선택 -->
    <v-card class="mb-2" variant="tonal" color="grey-darken-2">
      <v-card-subtitle class="d-flex justify-space-between align-center pb-0 pt-2">
        <span class="text-grey-lighten-1 font-weight-medium">
          <v-icon left size="small" class="mr-2">mdi-group</v-icon>
          {{ $t('filters.clusterSelection') }}
        </span>
        <div class="d-flex ga-1">
          <v-btn
            size="small"
            variant="text"
            color="grey-lighten-1"
            @click="deselectAllClusters"
            class="text-caption px-2"
          >
            {{ $t('filters.clearAll') }}
          </v-btn>
        </div>
      </v-card-subtitle>
      
      <v-card-text class="pt-1 pb-2 px-3">
        <!-- 클러스터 목록 -->
        <div class="cluster-list-container" :class="{ 'has-scroll': Object.keys(clusters).length > 5 }">
          <v-list density="compact" class="bg-transparent cluster-list">
            <!-- 클러스터가 없을 때 안내 메시지 -->
            <v-list-item v-if="Object.keys(clusters).length === 0" class="text-center py-3">
              <v-list-item-title class="text-grey-lighten-1 text-caption">
                <v-icon class="mr-2" size="small">mdi-loading</v-icon>
                {{ $t('filters.clusterLoading') }}
              </v-list-item-title>
            </v-list-item>
            
            <!-- 클러스터 목록 -->
            <v-list-item
              v-for="(cluster, clusterId) in clusters"
              :key="clusterId"
              class="cluster-item"
              :class="{ 'cluster-selected': selectedClusters.includes(clusterId) }"
            >
            <template v-slot:prepend>
              <v-checkbox
                :model-value="selectedClusters.includes(clusterId)"
                @update:model-value="toggleCluster(clusterId, $event)"
                hide-details
                color="grey-lighten-1"
                density="compact"
              ></v-checkbox>
            </template>

            <template v-slot:title>
              <div class="d-flex align-center">
                <div
                  class="cluster-color-indicator mr-3"
                  :style="{ backgroundColor: cluster.color }"
                ></div>
                <div class="cluster-info">
                  <div class="text-body-2 font-weight-medium text-white">{{ cluster.name }}</div>
                  <div class="text-caption text-grey-lighten-1">
                    <v-icon size="x-small" class="mr-1">mdi-image-multiple</v-icon>
                    {{ cluster.count }} {{ $t('filters.worksCount') }} 
                    <span v-if="cluster.year_range">
                      <v-icon size="x-small" class="mx-1">mdi-calendar</v-icon>
                      ({{ cluster.year_range }})
                    </span>
                  </div>
                </div>
              </div>
            </template>

            <template v-slot:append>
              <v-btn
                icon="mdi-information-outline"
                size="small"
                variant="text"
                color="grey-lighten-1"
                @click="showClusterInfo(cluster)"
              ></v-btn>
            </template>
          </v-list-item>
          </v-list>
        </div>
      </v-card-text>
    </v-card>



    <!-- 클러스터 정보 다이얼로그 -->
    <v-dialog v-model="clusterInfoDialog" max-width="600" :fullscreen="$vuetify.display.xs">
      <v-card v-if="selectedClusterInfo" dark color="grey-darken-3">
        <v-card-title class="bg-grey-darken-4 pa-4">
          <div class="d-flex align-center">
            <div
              class="cluster-color-indicator-large mr-3"
              :style="{ backgroundColor: selectedClusterInfo.color }"
            ></div>
            <div>
              <div class="text-h5 font-weight-medium">{{ selectedClusterInfo.name }}</div>
              <div class="text-subtitle-2 text-grey-lighten-2 mt-1">
                클러스터 상세 정보
              </div>
            </div>
          </div>
        </v-card-title>
        
        <v-card-text class="pa-4">
          <v-row>
            <v-col cols="12" md="6">
              <v-list lines="two" class="bg-transparent">
                <v-list-item>
                  <v-list-item-title class="text-grey-lighten-1">작품 수</v-list-item-title>
                  <v-list-item-subtitle class="text-white text-h6 font-weight-bold">{{ selectedClusterInfo.count }}개</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title class="text-grey-lighten-1">연도 범위</v-list-item-title>
                  <v-list-item-subtitle class="text-white">{{ selectedClusterInfo.year_range || 'N/A' }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
            <v-col cols="12" md="6">
              <v-list lines="two" class="bg-transparent">
                <v-list-item>
                  <v-list-item-title class="text-grey-lighten-1">주요 장르</v-list-item-title>
                  <v-list-item-subtitle class="text-white">{{ selectedClusterInfo.main_genre || 'N/A' }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title class="text-grey-lighten-1">주요 매체</v-list-item-title>
                  <v-list-item-subtitle class="text-white">{{ selectedClusterInfo.main_medium || 'N/A' }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
            
            <v-col cols="12" v-if="selectedClusterInfo.representative_works">
              <v-divider class="my-3 border-opacity-25"></v-divider>
              <h4 class="text-grey-lighten-1 mb-3">
                <v-icon left size="small">mdi-star-outline</v-icon>
                대표 작품들
              </h4>
              <v-list density="compact" class="bg-transparent">
                <v-list-item
                  v-for="work in selectedClusterInfo.representative_works"
                  :key="work.title"
                  class="px-0"
                >
                  <v-list-item-title class="text-body-2 text-white font-weight-medium">
                    {{ work.title }}
                  </v-list-item-title>
                    <v-list-item-subtitle class="text-grey-lighten-1">
                      <v-icon size="x-small" class="mr-1">mdi-account</v-icon>
                    {{ displayWorkArtist(work) }}, 
                    <v-icon size="x-small" class="mx-1">mdi-calendar</v-icon>
                    {{ work.year }}
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>

            <v-col cols="12" v-if="selectedClusterInfo.main_artists">
              <v-divider class="my-3 border-opacity-25"></v-divider>
              <h4 class="text-grey-lighten-1 mb-3">
                <v-icon left size="small">mdi-account-group</v-icon>
                주요 아티스트
              </h4>
              <div class="d-flex flex-wrap ga-2">
                <v-chip
                  v-for="(artist, index) in selectedClusterInfo.main_artists"
                  :key="`${artist}-${index}`"
                  size="small"
                  color="grey-lighten-1"
                  variant="tonal"
                  class="mb-1"
                >
                  {{ displayClusterArtist(artist, index) }}
                </v-chip>
              </div>
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions class="pa-4 pt-0">
          <v-spacer></v-spacer>
          <v-btn color="grey-lighten-1" variant="flat" @click="clusterInfoDialog = false">
            <v-icon left>mdi-close</v-icon>
            닫기
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { getLocalizedArtistName } from '../utils/artistTranslation'

export default {
  name: 'ClusterControls',
  props: {
    clusters: {
      type: Object,
      default: () => ({})
    },
    selectedClusters: {
      type: Array,
      default: () => []
    },
    allArtists: {
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
    searchOptions: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:selectedClusters', 'update:selectedArtists', 'update:searchQuery', 'filter-year'],
  data() {
    return {
      yearRange: [1980, 2023],
      clusterInfoDialog: false,
      selectedClusterInfo: null,
      artistSearchQuery: '', // 작가 검색용 쿼리
      
      // 연도 플레이 기능
      isPlaying: false,
      playTimer: null,
      playStartYear: 1980,
      playTargetYear: 2023,
      playCurrentEndYear: 1980,
      originalYearRange: [1980, 2023] // 원래 연도 범위 저장
    }
  },
  beforeUnmount() {
    // 컴포넌트 해제 시 타이머 정리
    this.stopPlay()
  },
  computed: {
    artistLabelMap() {
      const map = {}
      this.allArtists.forEach(artist => {
        const name = (artist?.name || '').trim()
        const nameKo = (artist?.nameKo || '').trim()
        if (name && nameKo) {
          map[name] = nameKo
        }
      })
      return map
    },
    // 검색된 작가 목록
    filteredArtists() {
      if (!this.artistSearchQuery || !this.artistSearchQuery.trim()) {
        return this.allArtists
      }
      
      const query = this.artistSearchQuery.toLowerCase().trim()
      return this.allArtists.filter(artist => 
        artist.name.toLowerCase().includes(query)
      )
    },

    // 선택된 작가들의 통계
    selectedArtistsStats() {
      if (this.selectedArtists.length === 0) return null
      
      const selectedArtistData = this.allArtists.filter(artist => 
        this.selectedArtists.includes(artist.name)
      )
      
      const totalWorks = selectedArtistData.reduce((sum, artist) => sum + artist.workCount, 0)
      const allClusters = new Set()
      selectedArtistData.forEach(artist => {
        artist.clusters.forEach(cluster => allClusters.add(cluster))
      })
      
      return {
        artistCount: selectedArtistData.length,
        totalWorks,
        clusterCount: allClusters.size
      }
    },

    // 작가 검색 자동완성 옵션
    artistSearchOptions() {
      if (!this.allArtists || !Array.isArray(this.allArtists)) {
        return []
      }
      
      return this.allArtists
        .filter(artist => artist && artist.name) // 유효한 작가만 필터링
        .map(artist => ({
          name: artist.name,
          nameKo: artist.nameKo || '',
          workCount: artist.workCount || 0,
          yearRangeText: artist.yearRangeText || 'N/A',
          clusters: artist.clusters || []
        }))
        .sort((a, b) => a.name.localeCompare(b.name)) // 알파벳 순 정렬
    }
  },
  watch: {
    clusters: {
      handler() {
        // 클러스터가 로드되면 초기에는 아무것도 선택하지 않음
        // 사용자가 필요에 따라 클러스터를 직접 선택하도록 함
      },
      immediate: true
    }
  },
  methods: {
    // 작가 이름 번역 메서드
    translateArtist(artistName) {
      const locale = (this.$i18n && this.$i18n.locale) ? this.$i18n.locale : 'en'
      return getLocalizedArtistName(artistName, this.artistLabelMap, locale)
    },

    displayWorkArtist(work) {
      if (!work) return ''
      const locale = (this.$i18n && this.$i18n.locale) ? this.$i18n.locale : 'en'
      const isKo = typeof locale === 'string' && locale.toLowerCase().startsWith('ko')
      return isKo && work.artist_ko ? work.artist_ko : work.artist
    },

    displayClusterArtist(artistName, index) {
      const locale = (this.$i18n && this.$i18n.locale) ? this.$i18n.locale : 'en'
      const isKo = typeof locale === 'string' && locale.toLowerCase().startsWith('ko')
      const koList = this.selectedClusterInfo?.main_artists_ko || []
      if (isKo && koList[index]) {
        return koList[index]
      }
      return artistName
    },
    
    toggleCluster(clusterId, selected) {
      let newSelection = [...this.selectedClusters]
      
      if (selected) {
        if (!newSelection.includes(clusterId)) {
          newSelection.push(clusterId)
        }
      } else {
        newSelection = newSelection.filter(id => id !== clusterId)
      }
      
      this.$emit('update:selectedClusters', newSelection)
    },



    deselectAllClusters() {
      this.$emit('update:selectedClusters', [])
    },

    onYearRangeChange() {
      this.$emit('filter-year', this.yearRange)
    },

    showClusterInfo(cluster) {
      this.selectedClusterInfo = cluster
      this.clusterInfoDialog = true
    },

    onArtistSelection(selectedArtists) {
      this.$emit('update:selectedArtists', selectedArtists)
    },

    toggleArtist(artistName) {
      const newSelection = [...this.selectedArtists]
      const index = newSelection.indexOf(artistName)
      
      if (index > -1) {
        newSelection.splice(index, 1)
      } else {
        newSelection.push(artistName)
      }
      
      this.$emit('update:selectedArtists', newSelection)
    },



    clearAllArtists() {
      this.$emit('update:selectedArtists', [])
    },

    updateSearchQuery(value) {
      this.$emit('update:searchQuery', value || '')
    },

    customFilter(value, query, item) {
      if (!query) return true
      
      const searchText = query.toLowerCase().trim()
      const itemTitle = (item.raw?.title || item.title || '').toLowerCase()
      const itemSubtitle = (item.raw?.subtitle || '').toLowerCase()
      
      // 단어 시작 부분 매칭을 우선하고, 부분 문자열 매칭도 지원
      const titleStartsWith = itemTitle.startsWith(searchText)
      const titleIncludes = itemTitle.includes(searchText)
      const subtitleIncludes = itemSubtitle.includes(searchText)
      
      return titleStartsWith || titleIncludes || subtitleIncludes
    },

    artistCustomFilter(value, query, item) {
      if (!query) return true
      
      const searchText = query.toLowerCase().trim()
      const originalName = (item.raw?.name || item.name || '').toLowerCase()
      
      // 번역된 이름도 검색 대상에 포함
      const translatedName = this.translateArtist(item.raw?.name || item.name || '').toLowerCase()
      
      // 원본 이름 매칭
      const originalStartsWith = originalName.startsWith(searchText)
      const originalIncludes = originalName.includes(searchText)
      const originalParts = originalName.split(' ')
      const originalPartMatches = originalParts.some(part => part.startsWith(searchText))
      
      // 번역된 이름 매칭
      const translatedStartsWith = translatedName.startsWith(searchText)
      const translatedIncludes = translatedName.includes(searchText)
      const translatedParts = translatedName.split(' ')
      const translatedPartMatches = translatedParts.some(part => part.startsWith(searchText))
      
      return originalStartsWith || originalIncludes || originalPartMatches ||
             translatedStartsWith || translatedIncludes || translatedPartMatches
    },

    onArtistSearchSelect(selectedArtist) {
      // clearable로 지울 때 null이 올 수 있으므로 안전하게 처리
      if (selectedArtist === null || selectedArtist === undefined) {
        this.artistSearchQuery = ''
        return
      }
      
      if (selectedArtist) {
        // 선택된 작가를 작가 선택 목록에 추가
        if (!this.selectedArtists.includes(selectedArtist)) {
          this.toggleArtist(selectedArtist)
        }
        // 검색어 초기화 (다음 검색을 위해)
        this.$nextTick(() => {
          this.artistSearchQuery = ''
        })
      }
    },

    updateStartYear(value) {
      const startYear = parseInt(value) || 1980
      
      // 유효성 검사
      if (startYear < 1980) return
      if (startYear > 2023) return
      if (startYear > this.yearRange[1]) return
      
      // yearRange 업데이트
      this.yearRange = [startYear, this.yearRange[1]]
      this.onYearRangeChange()
    },

    updateEndYear(value) {
      const endYear = parseInt(value) || 2023
      
      // 유효성 검사
      if (endYear < 1980) return
      if (endYear > 2023) return
      if (endYear < this.yearRange[0]) return
      
      // yearRange 업데이트
      this.yearRange = [this.yearRange[0], endYear]
      this.onYearRangeChange()
    },

    // 연도 플레이 기능
    togglePlay() {
      if (this.isPlaying) {
        this.stopPlay()
      } else {
        this.startPlay()
      }
    },

    startPlay() {
      // 원래 연도 범위 저장
      this.originalYearRange = [...this.yearRange]
      
      // 플레이 시작 설정
      this.playStartYear = this.yearRange[0]
      this.playTargetYear = this.yearRange[1]
      this.playCurrentEndYear = this.playStartYear
      
      // 현재 범위를 시작 연도로 설정
      this.yearRange = [this.playStartYear, this.playCurrentEndYear]
      this.onYearRangeChange()
      
      this.isPlaying = true
      
      // 1초마다 다음 연도로 진행
      this.playTimer = setInterval(() => {
        this.playStep()
      }, 1000)
    },

    stopPlay() {
      this.isPlaying = false
      if (this.playTimer) {
        clearInterval(this.playTimer)
        this.playTimer = null
      }
      
      // 원래 연도 범위로 복원
      this.yearRange = [...this.originalYearRange]
      this.onYearRangeChange()
    },

    playStep() {
      if (this.playCurrentEndYear >= this.playTargetYear) {
        // 플레이 완료
        this.stopPlay()
        return
      }
      
      // 다음 연도로 진행
      this.playCurrentEndYear++
      this.yearRange = [this.playStartYear, this.playCurrentEndYear]
      this.onYearRangeChange()
    }
  }
}
</script>

<style scoped>
.cluster-controls {
  padding: 8px 10px;
  background: transparent;
  display: flex;
  flex-direction: column;
}

/* 연도 슬라이더 컨테이너 - 툴팁 공간 확보 (컴팩트 버전) */
.year-slider-container {
  padding: 15px 12px 0px 12px;
  margin: 0 -8px 0 -8px;
  position: relative;
  z-index: 1;
}

/* 작은 화면에서 더 많은 여백 확보 */
@media (max-width: 1200px) {
  .year-slider-container {
    padding: 18px 16px 0px 16px;
    margin: 0 -12px 0 -12px;
  }
}

.cluster-color-indicator {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.cluster-color-indicator-large {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.7);
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
}

.cluster-item {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.2s ease;
  border-radius: 4px;
  margin: 0 !important;
  backdrop-filter: blur(2px);
  cursor: pointer;
}

.cluster-item:hover {
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.cluster-item.cluster-selected {
  background: rgba(var(--v-theme-primary), 0.15) !important;
  border-color: rgba(var(--v-theme-primary), 0.4);
  box-shadow: 0 2px 12px rgba(var(--v-theme-primary), 0.3);
}

.cluster-item:last-child {
  border-bottom: none;
}

.cluster-info {
  min-width: 0;
  flex: 1;
}

.cluster-info .text-caption {
  line-height: 1.3;
}

/* 클러스터 목록 컨테이너 높이 제한 */
.cluster-list-container {
  max-height: 280px;
  overflow-y: auto;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.2);
  position: relative;
}

/* 스크롤 가능할 때 시각적 힌트 */
.cluster-list-container.has-scroll::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: 4px;
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0.15), transparent);
  pointer-events: none;
  z-index: 2;
  border-radius: 4px 4px 0 0;
}

.cluster-list-container.has-scroll::after {
  content: '';
  position: absolute;
  bottom: 0;
  right: 0;
  left: 0;
  height: 4px;
  background: linear-gradient(to top, rgba(255, 255, 255, 0.15), transparent);
  pointer-events: none;
  z-index: 2;
  border-radius: 0 0 4px 4px;
}

/* 클러스터 리스트 스타일 */
.cluster-list {
  padding: 0 !important;
}

/* 클러스터 리스트 내부 패딩 완전 제거 */
.cluster-list-container .v-list {
  padding-top: 0 !important;
  padding-bottom: 0 !important; /* 아래 여백 완전 제거 */
  margin-bottom: 0 !important;
}

/* Vuetify 기본 스타일 강제 오버라이드 */
.cluster-list-container :deep(.v-list) {
  padding: 0 !important;
  margin: 0 !important;
}

.cluster-list-container :deep(.v-list-item) {
  margin-bottom: 0 !important;
}

.cluster-list-container :deep(.v-list-item:last-child) {
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}

/* 스크롤바 스타일링 */
.cluster-controls::-webkit-scrollbar {
  width: 6px;
}

.cluster-controls::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
}

.cluster-controls::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.cluster-controls::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Firefox 스크롤바 */
.cluster-controls {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) rgba(255, 255, 255, 0.05);
}

/* 클러스터 선택 카드 내부 스크롤 */
:deep(.v-card-text) {
  max-height: 300px;
  overflow-y: auto;
}

/* 애니메이션 */
.v-card {
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.v-card:hover {
  transform: translateY(-1px);
}

/* 카드 내부 패딩 최적화 */
.cluster-controls :deep(.v-card-subtitle) {
  padding-left: 12px;
  padding-right: 12px;
}

.cluster-controls :deep(.v-card-text) {
  padding-left: 12px;
  padding-right: 12px;
}

/* 다이얼로그 내부 스크롤바 */
.v-dialog :deep(.v-card-text) {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.3) rgba(255, 255, 255, 0.1);
  max-height: none;
}

/* Artist Selection 카드: 내부 스크롤 제거 및 높이 제한 해제 */
.artist-card-text {
  max-height: none !important;
  overflow: visible !important;
}

.v-dialog :deep(.v-card-text::-webkit-scrollbar) {
  width: 6px;
}

.v-dialog :deep(.v-card-text::-webkit-scrollbar-track) {
  background: rgba(255, 255, 255, 0.1);
}

.v-dialog :deep(.v-card-text::-webkit-scrollbar-thumb) {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

/* Gap 유틸리티 클래스 추가 */
.ga-2 {
  gap: 8px;
}

/* 검색 필드와 기타 고정 요소들 */
.fixed-controls {
  flex-shrink: 0;
}

/* 유연한 컨텐츠 영역 */
.flexible-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin: 2px 0;
}

/* 클러스터 선택 카드의 여백 최소화 */
.flexible-content .v-card {
  margin-bottom: 0 !important;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.flexible-content .v-card-text {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 컴팩트한 간격 조정 */
.cluster-controls > .fixed-controls + .flexible-content {
  margin-top: 4px;
}

.cluster-controls > .flexible-content + .fixed-controls {
  margin-top: 4px;
}

/* 전체 컨테이너 여백 최소화 */
.cluster-controls {
  gap: 4px; /* flexbox gap으로 일관된 간격 */
}

/* 마지막 고정 컨트롤의 여백 제거 */
.cluster-controls > .fixed-controls:last-child {
  margin-bottom: 0 !important;
}

/* 작가 선택 UI 스타일링: 카드 스크롤은 없음, 리스트는 스크롤 */
.artist-list-container {
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.2);
}

.artist-list {
  padding: 0 !important;
}

.artist-item {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.2s ease;
  cursor: pointer;
  margin: 0 !important;
}

.artist-item:hover {
  background: rgba(255, 255, 255, 0.05) !important;
}

.artist-item:last-child {
  border-bottom: none;
}

.artist-item.selected {
  background: rgba(255, 255, 255, 0.1) !important;
}

.artist-info {
  width: 100%;
  min-width: 0;
}

.artist-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 작가 리스트 스크롤바 스타일링 */
.artist-list-container::-webkit-scrollbar {
  width: 4px;
}

.artist-list-container::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.artist-list-container::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

.artist-list-container::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 통계 카드 스타일링 */
.artist-stats {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

/* 컴팩트한 칩 스타일 */
.artist-item .v-chip {
  min-width: 32px !important;
  height: 20px !important;
  font-size: 11px !important;
}



/* 반응형 클러스터 목록 높이 조정 */
@media (max-height: 700px) {
  .cluster-list-container {
    max-height: 180px; /* 작은 화면에서 더 컴팩트하게 */
  }
}

@media (min-height: 900px) {
  .cluster-list-container {
    max-height: 340px; /* 큰 화면에서 더 여유롭게 */
  }
}

@media (min-height: 1200px) {
  .cluster-list-container {
    max-height: 400px; /* 매우 큰 화면에서 최대 활용 */
  }
}

/* 클러스터 목록 스크롤바 스타일링 */
.cluster-list-container::-webkit-scrollbar {
  width: 4px;
}

.cluster-list-container::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.cluster-list-container::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

.cluster-list-container::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 연도 슬라이더 thumb-label 검은색 스타일 */
.black-thumb-label :deep(.v-slider-thumb__label) {
  background-color: #000000 !important;
  color: #ffffff !important;
}

.black-thumb-label :deep(.v-slider-thumb__label::before) {
  border-top-color: #000000 !important;
}

/* 연도 입력 필드 스타일 */
.year-input {
  max-width: 80px;
  min-width: 60px;
}

.year-input :deep(.v-field__input) {
  text-align: center;
  padding: 0 8px;
  font-size: 12px;
  color: white !important;
}

.year-input :deep(.v-field) {
  font-size: 12px;
}

.year-input :deep(input) {
  color: white !important;
}

/* 연도 필터 플레이 상태 스타일 */
.year-filter-card.playing {
  border: 1px solid rgba(244, 67, 54, 0.4) !important;
  box-shadow: 0 0 12px rgba(244, 67, 54, 0.2) !important;
  background: linear-gradient(135deg, rgba(244, 67, 54, 0.05), rgba(229, 57, 53, 0.03)) !important;
}

.year-filter-card.playing .v-card-subtitle {
  background: rgba(244, 67, 54, 0.1);
  border-radius: 4px 4px 0 0;
}

/* 플레이 버튼 스타일 */
.year-play-button {
  transition: all 0.2s ease !important;
  position: relative;
  z-index: 1;
}

/* 재생 버튼 (파란색) */
.year-play-button:not(.year-filter-card.playing .year-play-button) {
  background-color: #2196F3 !important;
  color: white !important;
}

.year-play-button:not(.year-filter-card.playing .year-play-button):hover {
  background-color: #1976D2 !important;
  transform: scale(1.05);
}

/* 정지 버튼 (빨간색) */
.year-filter-card.playing .year-play-button {
  background-color: #F44336 !important;
  color: white !important;
  animation: pulse-play 2s infinite ease-in-out;
  z-index: 1000 !important; /* 애니메이션 중에는 맨 위로 */
  position: relative;
}

.year-filter-card.playing .year-play-button:hover {
  background-color: #D32F2F !important;
}

/* 플레이 버튼 컨테이너 */
.play-button-container {
  position: relative;
  padding: 4px; /* 펄스 애니메이션 공간 확보 */
  z-index: 100;
}

.year-filter-card.playing .play-button-container {
  overflow: visible; /* 펄스 효과가 잘릴 수 있으므로 visible로 설정 */
}

/* 연도 카드 헤더 */
.year-card-header {
  position: relative;
  z-index: 1;
  overflow: visible; /* 펄스 애니메이션이 잘리지 않도록 */
}

.year-filter-card.playing .year-card-header {
  overflow: visible;
}

/* 플레이 버튼 애니메이션 */
@keyframes pulse-play {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.6);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 8px rgba(244, 67, 54, 0.2);
  }
}

/* 클러스터 컨테이너 높이 제한 */
.cluster-list-container {
  max-height: 240px;
  overflow-y: auto;
}

/* 클러스터 아이템 컴팩트 스타일 */
.cluster-list .v-list-item {
  padding: 8px 12px !important;
  margin-bottom: 4px;
  min-height: 48px;
}

.cluster-info {
  line-height: 1.3;
}

.cluster-info .text-body-2 {
  margin-bottom: 2px;
}

.cluster-info .text-caption {
  line-height: 1.2;
}

/* 컴팩트 요소들 */
.cluster-color-indicator {
  width: 10px !important;
  height: 10px !important;
}

.cluster-list .v-list-item .v-btn {
  transform: scale(0.9);
}
</style> 
