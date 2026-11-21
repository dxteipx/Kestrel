from kestrel.core import network

ENGLISH = """
Pinging 1.1.1.1 with 32 bytes of data:
Reply from 1.1.1.1: bytes=32 time=12ms TTL=57
Reply from 1.1.1.1: bytes=32 time<1ms TTL=57
Request timed out.
Reply from 1.1.1.1: bytes=32 time=15ms TTL=57

Ping statistics for 1.1.1.1:
    Packets: Sent = 4, Received = 3, Lost = 1 (25% loss),
Approximate round trip times in milli-seconds:
    Minimum = 1ms, Maximum = 15ms, Average = 9ms
"""

PORTUGUESE = """
Disparando 8.8.8.8 com 32 bytes de dados:
Resposta de 8.8.8.8: bytes=32 tempo=20ms TTL=117
Resposta de 8.8.8.8: bytes=32 tempo=22ms TTL=117
"""


def test_parse_reads_only_reply_lines():
    assert network.parse(ENGLISH) == (12, 1, 15)


def test_parse_works_in_other_languages():
    assert network.parse(PORTUGUESE) == (20, 22)


def test_result_statistics():
    result = network.PingResult("Test", "1.1.1.1", 4, (10, 20, 10))
    assert result.average == 40 / 3
    assert result.jitter == 10
    assert result.loss == 0.25
    assert result.quality == "Poor"  # a quarter of the packets lost


def test_quality_levels():
    assert network.PingResult("A", "x", 3, (8, 9, 10)).quality == "Great"
    assert network.PingResult("B", "x", 3, (45, 50, 55)).quality == "Good"
    assert network.PingResult("C", "x", 3, (120, 130, 140)).quality == "Poor"


def test_unreachable_host():
    result = network.PingResult("Test", "10.255.255.1", 4, ())
    assert result.average is None
    assert result.quality == "Unreachable"
