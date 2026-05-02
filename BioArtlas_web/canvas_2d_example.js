

    
// Canvas 2D 사용 예시
fetch('bioart_clustering_2d.json')
  .then(response => response.json())
  .then(data => {
    console.log(`총 ${data.metadata.statistics.total_artworks}개 작품 로드됨`);
    
    const canvas = document.getElementById('umap-canvas');
    const ctx = canvas.getContext('2d');
    
    // 뷰포트 설정
    const viewport = {
      x: 0,
      y: 0,
      scale: 1,
      width: canvas.width,
      height: canvas.height
    };
    
    // 좌표 변환 함수
    function worldToScreen(worldX, worldY) {
      return {
        x: (worldX * viewport.scale) + viewport.x,
        y: (worldY * viewport.scale) + viewport.y
      };
    }
    
    // 포인트 렌더링
    function renderPoints() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      data.points.forEach(point => {
        const cluster = data.clusters[point.cluster];
        const screenPos = worldToScreen(point.umapX, point.umapY);
        
        // 포인트 크기 (혁신가들은 더 크게)
        const radius = point.type === 'outlier' ? 8 : 5;
        
        // 그림자 효과
        ctx.shadowColor = 'rgba(0, 0, 0, 0.2)';
        ctx.shadowBlur = 3;
        ctx.shadowOffsetX = 1;
        ctx.shadowOffsetY = 1;
        
        // 포인트 그리기
        ctx.beginPath();
        ctx.arc(screenPos.x, screenPos.y, radius, 0, 2 * Math.PI);
        
        // 그라데이션 채우기
        const gradient = ctx.createRadialGradient(
          screenPos.x - radius/3, screenPos.y - radius/3, 0,
          screenPos.x, screenPos.y, radius
        );
        gradient.addColorStop(0, cluster.color);
        gradient.addColorStop(1, darkenColor(cluster.color, 0.3));
        
        ctx.fillStyle = gradient;
        ctx.fill();
        
        // 테두리
        ctx.shadowBlur = 0;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      });
    }
    
    // 색상 어둡게 만들기
    function darkenColor(color, factor) {
      const hex = color.replace('#', '');
      const r = Math.max(0, parseInt(hex.substr(0, 2), 16) * (1 - factor));
      const g = Math.max(0, parseInt(hex.substr(2, 2), 16) * (1 - factor));
      const b = Math.max(0, parseInt(hex.substr(4, 2), 16) * (1 - factor));
      return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
    }
    
    // 뷰포트 맞추기
    function fitViewport() {
      const xValues = data.points.map(p => p.umapX);
      const yValues = data.points.map(p => p.umapY);
      
      const xRange = { min: Math.min(...xValues), max: Math.max(...xValues) };
      const yRange = { min: Math.min(...yValues), max: Math.max(...yValues) };
      
      const dataWidth = xRange.max - xRange.min;
      const dataHeight = yRange.max - yRange.min;
      
      const padding = 0.1;
      const scaleX = viewport.width / (dataWidth * (1 + padding));
      const scaleY = viewport.height / (dataHeight * (1 + padding));
      
      viewport.scale = Math.min(scaleX, scaleY) * 0.9;
      viewport.x = (viewport.width - dataWidth * viewport.scale) / 2;
      viewport.y = (viewport.height - dataHeight * viewport.scale) / 2;
    }
    
    // 초기 렌더링
    fitViewport();
    renderPoints();
    
    // 편리한 필터링 함수들
    window.bioartFilters = {
      // 아티스트로 필터링
      byArtist: (artistName) => 
        data.points.filter(p => p.artist.includes(artistName)),
      
      // 연도 범위로 필터링  
      byYear: (startYear, endYear) => 
        data.points.filter(p => p.year >= startYear && p.year <= endYear),
      
      // 혁신가들만 필터링
      innovators: () => 
        data.points.filter(p => p.type === 'outlier'),
      
      // 클러스터로 필터링
      byCluster: (clusterId) => 
        data.points.filter(p => p.cluster === clusterId)
    };
    
    // 사용 예시
    console.log('Eduardo Kac 작품들:', bioartFilters.byArtist('Eduardo Kac'));
    console.log('2000년대 작품들:', bioartFilters.byYear(2000, 2009));
    console.log('혁신적 작품들:', bioartFilters.innovators());
  });
