import { chromium } from 'playwright';

async function testAdminDashboard() {
  console.log('🚀 Starting headless admin dashboard test...');
  
  let browser;
  try {
    // Launch browser
    browser = await chromium.launch();
    const page = await browser.newPage();
    
    // Listen for console logs and errors
    page.on('console', msg => {
      console.log(`📋 CONSOLE [${msg.type()}]: ${msg.text()}`);
    });
    
    page.on('pageerror', error => {
      console.log(`❌ PAGE ERROR: ${error.message}`);
    });
    
    page.on('requestfailed', request => {
      console.log(`🔴 FAILED REQUEST: ${request.method()} ${request.url()} - ${request.failure().errorText}`);
    });
    
    // Test health endpoint first
    console.log('\n🏥 Testing health endpoint...');
    const healthResponse = await page.goto('http://localhost:8001/admin/api/health');
    console.log(`Health status: ${healthResponse.status()}`);
    
    if (healthResponse.status() === 200) {
      const healthData = await healthResponse.json();
      console.log('✅ Health check passed:', healthData);
    }
    
    // Test admin login page
    console.log('\n🔐 Testing admin login page...');
    const loginResponse = await page.goto('http://localhost:8001/admin');
    console.log(`Admin page status: ${loginResponse.status()}`);
    
    // Wait a moment for any JS to load
    await page.waitForTimeout(2000);
    
    // Check for any errors in console
    const title = await page.title();
    console.log(`📄 Page title: "${title}"`);
    
    // Test API endpoints
    console.log('\n📊 Testing API endpoints...');
    
    // Try to access a protected endpoint (should get 401)
    try {
      const apiResponse = await page.goto('http://localhost:8001/admin/api/stats/overview');
      console.log(`Stats API status: ${apiResponse.status()}`);
      
      if (apiResponse.status() === 401) {
        console.log('✅ Protected endpoint correctly returns 401');
      }
    } catch (error) {
      console.log(`⚠️  API test error: ${error.message}`);
    }
    
    console.log('\n✨ Test completed successfully!');
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

// Run the test
testAdminDashboard().catch(error => {
  console.error('💥 Unhandled error:', error);
  process.exit(1);
});