import time
from fastapi import APIRouter, Depends, Request
from typing import List, Dict, Any, Set
from auth import get_api_key
from model_loader import get_vertex_models, get_vertex_express_models, refresh_models_config_cache
from credentials_manager import CredentialManager

router = APIRouter()
_last_model_fetch_time = 0  # 增加全局缓存时间戳

@router.get("/v1/models")
async def list_models(fastapi_request: Request, api_key: str = Depends(get_api_key)):
    global _last_model_fetch_time
    
    # 【Bug 修复】：1小时内只向 GitHub 请求一次，彻底避免被封杀和连接超时
    current_time = time.time()
    if current_time - _last_model_fetch_time > 3600:
        await refresh_models_config_cache()
        _last_model_fetch_time = current_time
    
    # 新增 FAKE 前缀
    FAKE_PREFIX = "[FAKE] "
    OPENAI_DIRECT_SUFFIX = "-openai"
    OPENAI_SEARCH_SUFFIX = "-openaisearch"
    
    # 仅保留对 Express 密钥的校验
    express_key_manager_instance = fastapi_request.app.state.express_key_manager

    has_express_key = express_key_manager_instance.get_total_keys() > 0
    raw_express_models = await get_vertex_express_models()
    
    final_model_list: List[Dict[str, Any]] = []
    processed_ids: Set[str] = set()

    def add_model_and_variants(base_id: str):
        suffixes = [""] 
        if "gemini" in base_id.lower():
            suffixes.append(OPENAI_DIRECT_SUFFIX)
            if not base_id.startswith("gemini-2.0"):
                suffixes.extend(["-search", OPENAI_SEARCH_SUFFIX])

        for suffix in suffixes:
            model_id_with_suffix = f"{base_id}{suffix}"
            # 默认不加前缀，直接作为标准模型 ID
            final_id = model_id_with_suffix
            
            # 1. 注入原本的模型
            if final_id not in processed_ids:
                final_model_list.append({
                    "id": final_id,
                    "object": "model",
                    "created": int(current_time),
                    "owned_by": "google",
                    "permission": [],
                    "root": base_id,
                    "parent": None
                })
                processed_ids.add(final_id)

            # 2. 注入带 [FAKE] 前缀的模型变体
            fake_final_id = f"{FAKE_PREFIX}{final_id}"
            if fake_final_id not in processed_ids:
                final_model_list.append({
                    "id": fake_final_id,
                    "object": "model",
                    "created": int(current_time),
                    "owned_by": "google",
                    "permission": [],
                    "root": base_id,
                    "parent": None
                })
                processed_ids.add(fake_final_id)

    if has_express_key:
        for model_id in raw_express_models: add_model_and_variants(model_id)

    return {"object": "list", "data": sorted(final_model_list, key=lambda x: x['id'])}