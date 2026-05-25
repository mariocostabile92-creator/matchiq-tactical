from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["system"])


def create_system_router(
    live_matches_cache,
    full_analysis_cache,
    scout_players_cache,
    live_matches_cache_seconds,
    full_analysis_cache_seconds,
    scout_players_cache_seconds,
    services_provider,
):
    @router.get("/health")
    def health_check():
        return {
            "status": "healthy",
            "version": "3.5.0",
            "auth": "online",
            "cache": {
                "live_matches_seconds": live_matches_cache_seconds,
                "full_analysis_seconds": full_analysis_cache_seconds,
                "scout_players_seconds": scout_players_cache_seconds,
                "live_matches_cached": len(live_matches_cache),
                "full_analysis_cached": len(full_analysis_cache),
                "scout_players_cached": len(scout_players_cache),
            },
            "services": services_provider(),
        }

    @router.get("/cache-status")
    def cache_status():
        return {
            "live_matches_cache": {
                "seconds": live_matches_cache_seconds,
                "keys": list(live_matches_cache.keys()),
                "count": len(live_matches_cache),
            },
            "full_analysis_cache": {
                "seconds": full_analysis_cache_seconds,
                "keys": list(full_analysis_cache.keys()),
                "count": len(full_analysis_cache),
            },
            "scout_players_cache": {
                "seconds": scout_players_cache_seconds,
                "keys": list(scout_players_cache.keys()),
                "count": len(scout_players_cache),
            },
        }

    @router.post("/clear-cache")
    def clear_cache():
        live_matches_cache.clear()
        full_analysis_cache.clear()
        scout_players_cache.clear()

        return {
            "success": True,
            "message": "Cache backend pulita correttamente",
        }

    return router