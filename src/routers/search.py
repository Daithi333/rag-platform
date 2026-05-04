from fastapi import APIRouter

from src.dependencies import OpenSearchDep, SettingsDep
from src.schemas.api.search import SearchRequest, SearchResponse
from src.services.embeddings.factory import make_embedding_client
from src.services.search import SearchService

router = APIRouter()


@router.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(
    request: SearchRequest,
    settings: SettingsDep,
    opensearch: OpenSearchDep,
) -> SearchResponse:
    """Search articles using BM25, vector, or hybrid search."""
    service = SearchService(
        opensearch=opensearch,
        embedding_client=make_embedding_client(),
        settings=settings.opensearch,
    )

    results = await service.search(
        query=request.query,
        mode=request.mode,
        tags=request.tags,
        size=request.size,
        from_=(request.page - 1) * request.size,
        sort_by_date=request.sort_by_date,
    )

    return SearchResponse(
        query=request.query,
        mode=request.mode,
        total=results["total"],
        page=request.page,
        size=request.size,
        hits=results["hits"],
    )
