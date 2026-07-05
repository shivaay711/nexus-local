# Distributed Rate Limiting Design Notes

## Token Bucket Algorithm
The token bucket algorithm refills tokens at a fixed rate and allows bursts up
to the bucket capacity. Each request consumes one token; requests are rejected
when the bucket is empty. Token bucket is memory-efficient because it stores
only two values per key: the token count and the last refill timestamp.

## Sliding Window Log
The sliding window log stores a timestamp for every request and counts entries
inside the window. It is perfectly accurate but memory usage grows linearly
with request rate, which makes it expensive for high-traffic keys.

## Sliding Window Counter
The sliding window counter interpolates between two fixed windows. It uses
constant memory per key and approximates the true rate with bounded error.

## Redis Synchronization
Distributed enforcement uses Redis with Lua scripts so that read-modify-write
operations on counters are atomic. A fail-open policy allows traffic when
Redis is unreachable; a fail-closed policy rejects traffic instead.
