#!/usr/bin/env python3
"""
HemoStat Test Worker Service

A background worker that simulates periodic resource spikes for demo scenarios.
Randomly spikes CPU or memory based on configured probability.
"""

import gc
import multiprocessing
import os
import random
import signal
import sys
import time

# Add parent directory to path to import HemoStatLogger
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agents.logger import HemoStatLogger

# Configure logging using HemoStat standard logger
logger = HemoStatLogger.get_logger('test-worker')

# Global flag for graceful shutdown
shutdown_flag = False


def cpu_stress_worker(end_time: float):
    """CPU stress worker process - runs tight loop until end_time"""
    while time.time() < end_time:
        # Tight loop to consume CPU
        _ = sum(i * i for i in range(1000))


def spike_cpu(duration: int):
    """Spike CPU usage for specified duration"""
    try:
        cpu_count = multiprocessing.cpu_count()
        num_workers = max(1, cpu_count)  # Use all CPUs for spike
        end_time = time.time() + duration
        
        logger.info(f"CPU spike started (duration: {duration}s, workers: {num_workers})")
        
        # Spawn worker processes
        processes = []
        for _ in range(num_workers):
            p = multiprocessing.Process(target=cpu_stress_worker, args=(end_time,))
            p.start()
            processes.append(p)
        
        # Wait for duration
        time.sleep(duration)
        
        # Terminate workers
        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=5)
        
        logger.info("CPU spike completed")
        
    except Exception as e:
        logger.error(f"CPU spike error: {e}")


def spike_memory(size_mb: int, duration: int):
    """Spike memory usage for specified duration"""
    try:
        logger.info(f"Memory spike started (size: {size_mb}MB, duration: {duration}s)")
        
        # Allocate memory (list of integers, ~8 bytes each)
        data = [0] * (size_mb * 1024 * 1024 // 8)
        
        # Hold memory for duration
        time.sleep(duration)
        
        # Release memory
        del data
        gc.collect()
        
        logger.info("Memory spike completed")
        
    except Exception as e:
        logger.error(f"Memory spike error: {e}")


def handle_shutdown(signum, frame):
    """Signal handler for graceful shutdown"""
    global shutdown_flag
    logger.info("Received shutdown signal")
    shutdown_flag = True


def worker_main():
    """Main worker loop"""
    # Read configuration from environment
    interval = int(os.getenv('WORKER_INTERVAL', '60'))
    spike_probability = float(os.getenv('WORKER_SPIKE_PROBABILITY', '0.1'))
    spike_duration = int(os.getenv('WORKER_SPIKE_DURATION', '30'))
    
    logger.info(f"Worker started (interval: {interval}s, spike_probability: {spike_probability})")
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    cycle_count = 0
    
    while not shutdown_flag:
        cycle_count += 1
        
        # Sleep for interval
        logger.info(f"Work cycle {cycle_count} starting...")
        time.sleep(interval)
        
        if shutdown_flag:
            break
        
        # Decide if spike should occur
        if random.random() < spike_probability:
            # Randomly choose CPU or memory spike
            spike_type = random.choice(['cpu', 'memory'])
            
            if spike_type == 'cpu':
                spike_cpu(spike_duration)
            else:
                # Allocate 500MB for memory spike
                spike_memory(500, spike_duration)
        else:
            logger.info(f"Work cycle {cycle_count} completed (no spike)")
    
    logger.info("Worker shutting down gracefully")


if __name__ == '__main__':
    try:
        worker_main()
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)
