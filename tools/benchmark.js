const fetch = require('node-fetch');

async function benchmark() {
  console.log('📊 Running performance benchmarks...');

  const tests = [
    { name: 'Health Check', url: '/api/health' },
    { name: 'Media Search', url: '/api/media/search?query=matrix&limit=5' },
    { name: 'Characters List', url: '/api/characters' },
    { name: 'Stats', url: '/api/stats' },
  ];

  for (const test of tests) {
    const start = Date.now();
    try {
      const response = await fetch(`http://localhost:8877${test.url}`);
      const duration = Date.now() - start;

      if (response.ok) {
        console.log(`✅ ${test.name}: ${duration}ms`);
      } else {
        console.log(`❌ ${test.name}: ${response.status} (${duration}ms)`);
      }
    } catch (error) {
      const duration = Date.now() - start;
      console.log(`❌ ${test.name}: Error (${duration}ms) - ${error.message}`);
    }
  }
}

benchmark();
