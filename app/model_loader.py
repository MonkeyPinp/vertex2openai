import httpx
import asyncio
import json
from typing import List, Dict, Optional, Any

import config as app_config 

_model_cache: Optional[Dict[str, List[str]]] = None
_cache_lock = asyncio.Lock()

async def fetch_and_parse_models_config() -> Optional[Dict[str, List[str]]]:
    if not app_config.MODELS_CONFIG_URL:
        print("📦 [模型配置] MODELS_CONFIG_URL 未设置")
        return None

    print(f"🌐 [模型配置] 正在获取远程模型配置：{app_config.MODELS_CONFIG_URL}")
    
    client_args = {'timeout': 20.0}
    if app_config.PROXY_URL:
        client_args['proxy'] = app_config.PROXY_URL
    if app_config.SSL_CERT_FILE:
        client_args['verify'] = app_config.SSL_CERT_FILE

    try:
        async with httpx.AsyncClient(**client_args) as client:
            response = await client.get(app_config.MODELS_CONFIG_URL)
            response.raise_for_status() 
            data = response.json()
            
            if isinstance(data, dict) and \
               "vertex_models" in data and isinstance(data["vertex_models"], list) and \
               "vertex_express_models" in data and isinstance(data["vertex_express_models"], list):
                print("✅ [模型配置] 远程模型配置加载成功。")
                return {
                    "vertex_models": data["vertex_models"],
                    "vertex_express_models": data["vertex_express_models"]
                }
            else:
                print(f"❌ [模型配置] 远程模型配置结构无效: {data}")
                return None
    except httpx.RequestError as e:
        print(f"⚠️ [模型配置] 获取远程模型配置失败，将回退到本地配置。网络错误：{e}")
        return None
    except json.JSONDecodeError as e:
        print(f"⚠️ [模型配置] 远程模型配置不是有效 JSON，将回退到本地配置。解析错误：{e}")
        return None
    except Exception as e:
        print(f"⚠️ [模型配置] 加载远程模型配置时出现异常，将回退到本地配置：{e}")
        return None

async def get_models_config() -> Dict[str, List[str]]:
    global _model_cache
    async with _cache_lock:
        if _model_cache is None:
            print("📦 [模型配置] 缓存为空，正在初始化模型列表。")
            _model_cache = await fetch_and_parse_models_config()
            if _model_cache is None: 
                print("⚠️ [模型配置] 模型配置初始化失败，当前模型列表为空。")
                _model_cache = {"vertex_models": [], "vertex_express_models": []}
    return _model_cache

async def get_vertex_models() -> List[str]:
    config = await get_models_config()
    return config.get("vertex_models", [])

async def get_vertex_express_models() -> List[str]:
    config = await get_models_config()
    return config.get("vertex_express_models", [])

async def refresh_models_config_cache() -> bool:
    global _model_cache
    print("🔄 [模型配置] 正在刷新模型配置缓存。")
    async with _cache_lock:
        new_config = await fetch_and_parse_models_config()
        if new_config is not None:
            _model_cache = new_config
            print("✅ [模型配置] 模型配置缓存刷新成功。")
            return True
        else:
            print("❌ [模型配置] 模型配置缓存刷新失败。")
            return False