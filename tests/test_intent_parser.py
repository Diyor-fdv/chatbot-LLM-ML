from app.services.intent_parser import parse_intent
from app.services.semantic_layer import get_semantic_layer


def test_parse_top_n_profit_products():
    layer = get_semantic_layer()
    intent = parse_intent("Top 5 products by profit", layer=layer)
    assert intent.metric in ("profit", "revenue")
    assert intent.top_n == 5

