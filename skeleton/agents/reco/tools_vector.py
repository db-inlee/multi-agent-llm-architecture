"""벡터 검색 도구 스키마 (OpenAI Function Calling용)."""

# LLM이 function calling으로 호출하는 제품 검색 도구 정의
VECTOR_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_products",
        "description": "피부 고민이나 제품 특성으로 제품을 시맨틱 검색",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "자연어 검색 쿼리 (피부 고민, 효과, 성분 등)",
                },
                "category": {
                    "type": "string",
                    "enum": ["토너", "세럼", "크림", "선크림", "클렌저", "로션", "패드", "미스트", "아이크림"],
                    "description": "제품 카테고리 (사용자가 특정 유형 원할 때만)",
                },
                "sub_category": {
                    "type": "string",
                    "description": "서브카테고리 필터 (선택)",
                },
                "skin_type": {
                    "type": "string",
                    "enum": ["dry", "oily", "combination", "sensitive", "normal"],
                    "description": "피부 타입 필터 (선택)",
                },
                "price_max": {
                    "type": "integer",
                    "description": "최대 가격 (원)",
                },
                "top_k": {
                    "type": "integer",
                    "description": "반환할 제품 수 (기본 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
}

# 에이전트 시스템 프롬프트 — 실제 내용은 제거됨
# AGENT_SYSTEM_PROMPT = """[도메인 전문가 역할 + 도구 사용 가이드]"""
