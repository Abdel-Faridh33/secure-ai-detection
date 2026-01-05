"""
Performance tests - Latency
"""

import time

def test_inference_latency():
    """Test inference latency"""
    start = time.time()
    # Run inference
    latency = time.time() - start
    assert latency < 0.1  # Max 100ms
