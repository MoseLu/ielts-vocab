const https = require('https');
const crypto = require('crypto');

const SECRET = 'idictation_2024';

/**
 * Generate the request signature for idictation.cn API
 */
function generateSignature(data, urlPath) {
  // Lae: filter null/undefined
  const filtered = Object.keys(data).reduce((acc, key) => {
    if (data[key] !== undefined && data[key] !== null) {
      acc[key] = data[key];
    }
    return acc;
  }, {});

  // Vae: add api_key, timestamp, nonce
  filtered['api_key'] = encodeURIComponent(urlPath);
  filtered['timestamp'] = Math.floor(Date.now() / 1000);
  filtered['nonce'] = Math.random().toString(36).substring(2, 12);

  // zae: sort keys, build query string
  const sortedKeys = Object.keys(filtered).sort();
  let queryStr = '';
  for (const key of sortedKeys) {
    let val = filtered[key];
    if (Array.isArray(val) || (typeof val === 'object' && val !== null)) {
      val = JSON.stringify(val);
    }
    queryStr += key + '=' + val + '&';
  }
  queryStr = queryStr.replace(/&$/, '');

  // HMAC-SHA256
  const sign = crypto.createHmac('sha256', SECRET).update(queryStr).digest('hex');

  return { ...filtered, sign };
}

/**
 * Make an authenticated API request
 */
function apiRequest(path, body = {}) {
  const { sign, timestamp, nonce, api_key, ...data } = generateSignature(body, path);

  const postData = JSON.stringify(data);
  const options = {
    hostname: 'www.idictation.cn',
    path: path,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(postData),
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      'Accept': 'application/json, text/plain, */*',
      'Origin': 'https://www.idictation.cn',
      'Referer': 'https://www.idictation.cn/main/book',
    }
  };

  return new Promise((resolve, reject) => {
    const req = https.request(options, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        try {
          resolve(JSON.parse(d));
        } catch(e) {
          resolve(d);
        }
      });
    });
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

async function main() {
  console.log('=== 爱听写 API 探查 ===\n');

  // 1. 公开接口 - 词库分类
  console.log('--- 词库分类 ---');
  const lang = await apiRequest('/api/study/lexicon/v1/language/list', {});
  console.log(JSON.stringify(lang, null, 2));

  // 2. 公开接口 - 分类列表 (留学/小学/初中/高中/大学/其他)
  console.log('\n--- 分类列表 ---');
  const cat = await apiRequest('/api/study/lexicon/v1/v1/category/list', {});
  console.log(JSON.stringify(cat, null, 2));

  // 3. 词书列表 (scene/list with language_id=5)
  console.log('\n--- 词书场景列表 (language_id=5) ---');
  const scenes = await apiRequest('/api/study/lexicon/v1/scene/list', { language_id: 5 });
  console.log(JSON.stringify(scenes, null, 2));

  // 4. 精听场景列表 (language_id=4)
  console.log('\n--- 精听场景列表 (language_id=4) ---');
  const jtScenes = await apiRequest('/api/study/lexicon/v1/scene/list', { language_id: 4 });
  console.log(JSON.stringify(jtScenes, null, 2));

  // 5. 尝试登录
  console.log('\n--- 登录测试 ---');
  const login = await apiRequest('/api/study/customer/v1/login', { phone: '13800000001', password: 'test123' });
  console.log(JSON.stringify(login, null, 2));
  if (login.session_ids) {
    console.log('\n登录成功！Token:', login.session_ids);
  }
}

main().catch(console.error);
