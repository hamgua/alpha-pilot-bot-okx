"""
代理配置示例
展示如何配置和使用CDN代理来优化API连接
"""

# 代理配置示例
PROXY_CONFIG = {
    # 是否启用代理支持
    'use_proxy': True,

    # 代理服务配置
    'proxies': [
        {
            'url': 'https://your-worker.your-subdomain.workers.dev/proxy',
            'type': 'cloudflare_workers',
            'region': 'global',
            'weight': 1.0,
            'timeout_bonus': 1.2,
            'api_key': 'your-worker-api-key'  # 如果代理需要认证
        },
        {
            'url': 'https://api.cloudflare.com/client/v4/accounts/YOUR_ACCOUNT_ID/workers/scripts/YOUR_WORKER',
            'type': 'cloudflare_api',
            'region': 'global',
            'weight': 0.9,
            'timeout_bonus': 1.1,
            'headers': {
                'X-Auth-Email': 'your-email@example.com',
                'X-Auth-Key': 'your-global-api-key'
            }
        },
        {
            'url': 'https://cors-anywhere.herokuapp.com',
            'type': 'cors_proxy',
            'region': 'us',
            'weight': 0.8,
            'timeout_bonus': 1.5,
            'origin_header': True  # 需要添加Origin头
        }
    ],

    # 代理选择策略
    'selection_policy': {
        'mode': 'adaptive',  # adaptive, random, sequential
        'fallback_to_direct': True,  # 代理失败时回退到直接连接
        'max_failures': 3,  # 最大失败次数
        'failure_reset_time': 3600  # 失败重置时间（秒）
    },

    # 超时配置增强
    'timeout_config': {
        'proxy_connection_timeout': 15.0,
        'proxy_response_timeout': 30.0,
        'proxy_total_timeout': 60.0,
        'direct_connection_timeout': 10.0,
        'direct_response_timeout': 20.0,
        'direct_total_timeout': 40.0
    },

    # 哪些API提供商使用代理
    'proxy_targets': [
        'api.deepseek.com',
        'api.moonshot.cn',
        'dashscope.aliyuncs.com',
        'api.openai.com',
        'api.anthropic.com',
        'api.groq.com'
    ],

    # 地理优化
    'geo_optimization': {
        'enabled': True,
        'prefer_nearby': True,
        'regions': {
            'cn': ['ap-east-1', 'ap-southeast-1'],
            'us': ['us-east-1', 'us-west-1'],
            'eu': ['eu-west-1', 'eu-central-1']
        }
    }
}

# Cloudflare Worker 示例代码
CLOUDFLARE_WORKER_CODE = '''
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  const targetUrl = url.searchParams.get('url')

  if (!targetUrl) {
    return new Response('Missing URL parameter', { status: 400 })
  }

  try {
    // 转发请求到目标URL
    const response = await fetch(targetUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body
    })

    // 创建新的响应，添加CORS头
    const newResponse = new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers
    })

    newResponse.headers.set('Access-Control-Allow-Origin', '*')
    newResponse.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    newResponse.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    return newResponse
  } catch (error) {
    return new Response(`Proxy error: ${error.message}`, { status: 500 })
  }
}
'''

# 使用说明
USAGE_INSTRUCTIONS = """
代理配置使用说明：

1. 启用代理支持：
   - 在config.yaml中设置 ai.use_proxy: true
   - 或者在环境变量中设置 AI_USE_PROXY=true

2. 部署Cloudflare Worker代理：
   - 登录Cloudflare控制台
   - 创建新的Worker
   - 粘贴上面的Worker代码
   - 部署并获得Worker URL

3. 配置自定义代理：
   - 在环境变量中设置 CUSTOM_PROXIES=json_array格式
   - 例如：CUSTOM_PROXIES='[{"url":"https://proxy1.com","weight":1.0}]'

4. 验证代理是否生效：
   - 查看日志中的代理请求成功/失败信息
   - 使用 get_proxy_recommendations() 获取代理统计

5. 故障排除：
   - 如果代理持续失败，会自动回退到直接连接
   - 可以调用 reset_failed_proxies() 重置失败状态
   - 代理统计信息可以帮助选择最佳代理
"""

# 性能优化建议
PERFORMANCE_TIPS = """
代理性能优化建议：

1. 选择就近的代理服务器以减少延迟
2. 使用权重调整不同代理的使用频率
3. 监控代理的成功率并调整配置
4. 为不同地区的用户配置不同的代理
5. 定期更新代理列表，移除失效的代理
6. 考虑使用付费的专业代理服务
7. 实现代理健康检查机制
""

# 环境变量配置
ENVIRONMENT_CONFIG = {
    'AI_USE_PROXY': '是否启用代理 (true/false)',
    'CUSTOM_PROXIES': '自定义代理列表 (JSON格式)',
    'PROXY_TIMEOUT_BONUS': '代理超时时间倍数 (默认1.2)',
    'PROXY_MAX_FAILURES': '代理最大失败次数 (默认3)',
    'PROXY_FAILURE_RESET_TIME': '代理失败重置时间秒数 (默认3600)'
}