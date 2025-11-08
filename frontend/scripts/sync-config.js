const fs = require('fs');
const path = require('path');

// Read .env file from src/embedder
const envPath = path.join(__dirname, '../../src/embedder/.env');
const configPath = path.join(__dirname, '../public/config.js');

try {
  const envContent = fs.readFileSync(envPath, 'utf8');
  const envVars = {};
  
  envContent.split('\n').forEach(line => {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const [key, ...valueParts] = trimmed.split('=');
      if (key && valueParts.length > 0) {
        const value = valueParts.join('=').trim();
        if (key.startsWith('SUPABASE_')) {
          envVars[key] = value;
        }
      }
    }
  });

  const configContent = `// Auto-generated from .env file
// Do not edit manually - run: node scripts/sync-config.js
window.env = {
  SUPABASE_URL: '${envVars.SUPABASE_URL || ''}',
  SUPABASE_ANON_KEY: '${envVars.SUPABASE_ANON_KEY || ''}'
};
`;

  fs.writeFileSync(configPath, configContent, 'utf8');
  console.log('✅ Config synced successfully!');
  console.log('📝 Make sure SUPABASE_ANON_KEY in .env has your actual anon key (not "your_anon_key_here")');
} catch (error) {
  console.error('❌ Error syncing config:', error.message);
  process.exit(1);
}

