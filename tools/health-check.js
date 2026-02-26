const fetch = require('node-fetch');

async function healthCheck() {
  try {
    const response = await fetch('http://localhost:8877/api/health');
    const data = await response.json();

    if (data.status === 'healthy') {
      console.log('✅ System is healthy');
      return true;
    } else {
      console.log('❌ System unhealthy:', data);
      return false;
    }
  } catch (error) {
    console.log('❌ Health check failed:', error.message);
    return false;
  }
}

healthCheck().then((healthy) => process.exit(healthy ? 0 : 1));
