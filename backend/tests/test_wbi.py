"""wbi 签名单测：使用社区公开文档的测试向量，不发网络请求。"""
from app.services.transcript.wbi import mixin_key_from, sign

# 公开文档广泛引用的测试密钥对
IMG_KEY = "7cd084941338484aae1ad9425b84077c"
SUB_KEY = "4932caff0ff746eab6f01bf08b70ac45"


def test_mixin_key_vector():
    key = mixin_key_from(IMG_KEY, SUB_KEY)
    # 社区公开文档中该测试向量公认的结果
    assert key == "ea1db124af3c7062474693fa704f4ff8"


def test_sign_deterministic():
    params = {"bvid": "BV1xx411c7mD", "cid": "123"}
    a = sign(params, "k" * 32, ts=1700000000)
    b = sign(dict(reversed(list(params.items()))), "k" * 32, ts=1700000000)
    # 与参数传入顺序无关（内部排序）
    assert a == b
    assert a["wts"] == "1700000000"
    assert len(a["w_rid"]) == 32
    int(a["w_rid"], 16)  # 必须是合法 hex


def test_sign_strips_special_chars():
    p = sign({"q": "a!(b)*c"}, "k" * 32, ts=1700000000)
    assert p["q"] == "abc"
