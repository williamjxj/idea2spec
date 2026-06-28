"""Tests for _extract_json — the LLM JSON extraction helper.

These test the edge cases that cause intermittent failures:
- Chinese preamble before JSON
- Postamble text after JSON
- Markdown code fences
- <think> reasoning blocks
- Plain valid JSON
- Nested braces
"""

import json

import pytest

from services.llm_router.router import _extract_json


def test_plain_json():
    text = '{"market": "test", "competitors": [], "monetization": "freemium"}'
    result = _extract_json(text)
    assert result["market"] == "test"
    assert result["competitors"] == []
    assert result["monetization"] == "freemium"


def test_json_with_chinese_preamble():
    """LLM adds a friendly preamble before the JSON — most common failure mode."""
    text = """好的，这是蒙特梭利儿童在线教育系统的市场分析：

{
  "market": "温哥华儿童教育市场规模约5000万加元，年增长率8%",
  "competitors": ["ABC Learning", "XYZ Education"],
  "monetization": "订阅制，每月$49"
}

希望这个分析对您有帮助！"""
    result = _extract_json(text)
    assert "温哥华" in result["market"]
    assert len(result["competitors"]) == 2


def test_json_with_postamble_only():
    text = """{
  "market": "test market",
  "competitors": [],
  "monetization": "ads"
}
以上是分析结果。"""
    result = _extract_json(text)
    assert result["market"] == "test market"


def test_markdown_fence_with_json_tag():
    text = """```json
{
  "market": "test",
  "competitors": ["A", "B"],
  "monetization": "subscription"
}
```"""
    result = _extract_json(text)
    assert result["competitors"] == ["A", "B"]


def test_markdown_fence_without_json_tag():
    text = """```
{
  "market": "test",
  "competitors": [],
  "monetization": ""
}
```"""
    result = _extract_json(text)
    assert result["market"] == "test"


def test_markdown_fence_with_preamble():
    """Markdown fence with Chinese text before and after."""
    text = """以下是分析结果：

```json
{
  "market": "温哥华市场分析",
  "competitors": ["Comp1"],
  "monetization": "订阅制"
}
```

如有问题请告知。"""
    result = _extract_json(text)
    assert "温哥华" in result["market"]


def test_think_tags_are_stripped():
    text = """<think>
Let me analyze the market for this idea.
The market is growing at 8% annually.
</think>
{
  "market": "test market with think tags",
  "competitors": [],
  "monetization": "ads"
}"""
    result = _extract_json(text)
    assert "think tags" in result["market"]


def test_think_tags_with_chinese():
    text = """<think>
用户想要一个蒙特梭利儿童在线教育系统。
让我分析一下温哥华的市场...
</think>
好的，这是分析结果：

{
  "market": "温哥华蒙特梭利教育市场",
  "competitors": ["A", "B", "C"],
  "monetization": "混合模式"
}"""
    result = _extract_json(text)
    assert "蒙特梭利" in result["market"]
    assert len(result["competitors"]) == 3


def test_nested_braces_in_strings():
    """JSON with braces inside string values should still parse correctly."""
    text = """Some preamble text here.

{
  "market": "Market analysis {detailed} with braces",
  "competitors": ["A {suffix}", "B"],
  "monetization": "Plan: {tier1: $10, tier2: $20}"
}

End of response."""
    result = _extract_json(text)
    assert "{detailed}" in result["market"]
    assert "{suffix}" in result["competitors"][0]


def test_invalid_json_raises():
    """Text with no JSON at all should raise JSONDecodeError."""
    text = "This is just plain text with no JSON object anywhere."
    with pytest.raises(json.JSONDecodeError):
        _extract_json(text)


def test_truncated_json_raises():
    """Unclosed brace should raise JSONDecodeError."""
    text = '{"market": "test", "competitors": ['
    with pytest.raises(json.JSONDecodeError):
        _extract_json(text)


def test_preamble_and_postamble_no_fence():
    """The most realistic Chinese LLM output — no markdown, just friendly text."""
    text = """好的，我来为您分析蒙特梭利儿童在线教育系统的市场。

{
  "market": "温哥华拥有约5万名3-12岁儿童，蒙特梭利教育需求持续增长。在线教育市场年增长率约12%，疫情后家长对混合式学习接受度显著提高。",
  "competitors": [
    "Montessori Academy of Vancouver - 本地最大蒙特梭利连锁",
    "Guidepost Montessori - 北美品牌，提供线上课程",
    "Outschool - 美国在线教育平台，有蒙特梭利类课程",
    "Khan Academy Kids - 免费儿童教育应用",
    "ABCmouse - 订阅制早教平台"
  ],
  "monetization": "分层订阅模式：基础免费版（含广告），高级版$14.99/月，家庭版$24.99/月（最多3个孩子）。企业版面向学校，按学生人数收费。"
}

以上就是我的分析，希望能帮助您更好地理解市场机会。如果您需要更详细的某个方面的分析，请告诉我！"""
    result = _extract_json(text)
    assert "温哥华" in result["market"]
    assert len(result["competitors"]) == 5
    assert "$14.99" in result["monetization"]
