"""resolver 纯函数部分单测（不发网络请求）。"""
import pytest

from app.services.resolver import BILI_BV_RE, B23_RE, DOUYIN_RE, extract_first_url


def test_b23_short_link():
    text = "【B站】10分钟学会 https://b23.tv/abCd3f 快来看"
    assert extract_first_url(text) == "https://b23.tv/abCd3f"


def test_bilibili_bv():
    text = "https://www.bilibili.com/video/BV1xx411c7mD?spm_id_from=333"
    m = BILI_BV_RE.search(text)
    assert m and m.group(1) == "BV1xx411c7mD"


def test_douyin():
    text = "8.99 复制打开抖音 https://v.douyin.com/iRNBho5/ 看视频"
    m = DOUYIN_RE.search(text)
    assert m and m.group(0).startswith("https://v.douyin.com/")


def test_no_url():
    assert extract_first_url("随便一段话没有链接") is None
