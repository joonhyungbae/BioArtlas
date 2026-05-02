const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  
  // GitHub Pages와 사용자 정의 도메인(bioartlas.com)을 위한 설정
  publicPath: process.env.NODE_ENV === 'production' ? '/' : '/',
  
  // 페이지 타이틀 설정
  chainWebpack: config => {
    config
      .plugin('html')
      .tap(args => {
        args[0].title = 'BioArtlas'
        return args
      })
  },
  
  // 빌드 출력 디렉토리
  outputDir: 'dist',
  
  // 정적 에셋 디렉토리
  assetsDir: 'assets',
  
  // 빌드시 소스맵 생성하지 않음 (배포시 성능 향상)
  productionSourceMap: false,
  
  // Vuetify 설정
  pluginOptions: {
    vuetify: {
      // Vuetify 관련 설정이 필요하면 여기에 추가
    }
  },
  
  // 개발 서버 설정
  devServer: {
    port: 8080,
    open: true
  }
})
