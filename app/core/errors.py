from __future__ import annotations


class AppError(Exception):
    """Base application error."""


class UnsafeQueryError(AppError):
    pass


class SemanticLayerError(AppError):
    pass


class QueryBuildError(AppError):
    pass

