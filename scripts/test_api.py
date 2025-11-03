#!/usr/bin/env python3
"""
HemoStat Test API Service

A simple Flask application that provides HTTP endpoints for triggering
resource stress tests. Used for demo scenarios and integration testing.
"""

import json
import multiprocessing
import os
import signal
import sys
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from flask import Flask, request, jsonify
    import psutil
except ImportError:
    print("Installing required dependencies...", file=sys.stderr)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "flask", "psutil"])
    from flask import Flask, request, jsonify
    import psutil

# Add parent directory to path to import HemoStatLogger
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agents.logger import HemoStatLogger

# Configure logging using HemoStat standard logger
logger = HemoStatLogger.get_logger('test-api')

app = Flask(__name__)

# Global state for active stress tests
active_tests: Dict[str, Any] = {}
active_tests_lock = threading.Lock()


def cpu_stress_worker(duration: int, end_time: float):
    """CPU stress worker process - runs tight loop until end_time"""
    while time.time() < end_time:
        # Tight loop to consume CPU
        _ = sum(i * i for i in range(1000))


def run_cpu_stress(duration: int, intensity: float):
    """Spawn CPU stress workers based on intensity"""
    try:
        cpu_count = multiprocessing.cpu_count()
        num_workers = max(1, int(cpu_count * intensity))
        end_time = time.time() + duration
        
        logger.info(f"Starting CPU stress: {num_workers} workers for {duration}s (intensity: {intensity})")
        
        # Spawn worker processes
        processes = []
        for _ in range(num_workers):
            p = multiprocessing.Process(target=cpu_stress_worker, args=(duration, end_time))
            p.start()
            processes.append(p)
        
        with active_tests_lock:
            active_tests['cpu'] = {
                'type': 'cpu',
                'processes': processes,
                'end_time': end_time,
                'duration': duration,
                'intensity': intensity
            }
        
        # Wait for duration then cleanup
        time.sleep(duration)
        
        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=5)
        
        with active_tests_lock:
            if 'cpu' in active_tests:
                del active_tests['cpu']
        
        logger.info("CPU stress completed")
        
    except Exception as e:
        logger.error(f"CPU stress error: {e}")
        with active_tests_lock:
            if 'cpu' in active_tests:
                del active_tests['cpu']


def run_memory_stress(duration: int, size_mb: int):
    """Allocate memory for specified duration"""
    try:
        logger.info(f"Starting memory stress: {size_mb}MB for {duration}s")
        
        # Allocate memory (list of integers, ~8 bytes each)
        data = [0] * (size_mb * 1024 * 1024 // 8)
        
        with active_tests_lock:
            active_tests['memory'] = {
                'type': 'memory',
                'data': data,
                'size_mb': size_mb,
                'duration': duration,
                'end_time': time.time() + duration
            }
        
        # Hold memory for duration
        time.sleep(duration)
        
        # Release memory
        with active_tests_lock:
            if 'memory' in active_tests:
                del active_tests['memory']
        
        logger.info("Memory stress completed")
        
    except Exception as e:
        logger.error(f"Memory stress error: {e}")
        with active_tests_lock:
            if 'memory' in active_tests:
                del active_tests['memory']


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200


@app.route('/stress/cpu', methods=['POST'])
def stress_cpu():
    """Trigger CPU stress test"""
    try:
        data = request.get_json() or {}
        duration = data.get('duration', 60)
        intensity = data.get('intensity', 0.9)
        
        # Validate inputs
        if not (1 <= duration <= 300):
            return jsonify({'error': 'duration must be 1-300 seconds'}), 400
        if not (0.0 <= intensity <= 1.0):
            return jsonify({'error': 'intensity must be 0.0-1.0'}), 400
        
        # Check if CPU stress already running
        with active_tests_lock:
            if 'cpu' in active_tests:
                return jsonify({'error': 'CPU stress already running'}), 409
        
        # Start stress test in background thread
        thread = threading.Thread(target=run_cpu_stress, args=(duration, intensity), daemon=True)
        thread.start()
        
        return jsonify({
            'status': 'started',
            'duration': duration,
            'intensity': intensity
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting CPU stress: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/stress/memory', methods=['POST'])
def stress_memory():
    """Trigger memory stress test"""
    try:
        data = request.get_json() or {}
        duration = data.get('duration', 60)
        size_mb = data.get('size_mb', 500)
        
        # Validate inputs
        if not (1 <= duration <= 300):
            return jsonify({'error': 'duration must be 1-300 seconds'}), 400
        if not (1 <= size_mb <= 2000):
            return jsonify({'error': 'size_mb must be 1-2000'}), 400
        
        # Check if memory stress already running
        with active_tests_lock:
            if 'memory' in active_tests:
                return jsonify({'error': 'Memory stress already running'}), 409
        
        # Start stress test in background thread
        thread = threading.Thread(target=run_memory_stress, args=(duration, size_mb), daemon=True)
        thread.start()
        
        return jsonify({
            'status': 'started',
            'duration': duration,
            'size_mb': size_mb
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting memory stress: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/stress/stop', methods=['POST'])
def stress_stop():
    """Stop all active stress tests"""
    try:
        stopped_count = 0
        
        with active_tests_lock:
            # Stop CPU stress
            if 'cpu' in active_tests:
                processes = active_tests['cpu'].get('processes', [])
                for p in processes:
                    if p.is_alive():
                        p.terminate()
                        p.join(timeout=5)
                del active_tests['cpu']
                stopped_count += 1
            
            # Stop memory stress
            if 'memory' in active_tests:
                del active_tests['memory']
                stopped_count += 1
        
        logger.info(f"Stopped {stopped_count} active stress tests")
        
        return jsonify({
            'status': 'stopped',
            'tests_stopped': stopped_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping stress tests: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Get current resource metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        active_test_list = []
        with active_tests_lock:
            for test_type, test_data in active_tests.items():
                active_test_list.append({
                    'type': test_type,
                    'end_time': test_data.get('end_time'),
                    'remaining': max(0, test_data.get('end_time', 0) - time.time())
                })
        
        return jsonify({
            'cpu_percent': round(cpu_percent, 1),
            'memory_percent': round(memory.percent, 1),
            'memory_used_mb': round(memory.used / (1024 * 1024), 1),
            'memory_total_mb': round(memory.total / (1024 * 1024), 1),
            'active_tests': active_test_list,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({'error': str(e)}), 500


def cleanup_on_exit(signum, frame):
    """Cleanup handler for graceful shutdown"""
    logger.info("Shutting down gracefully...")
    
    with active_tests_lock:
        # Stop CPU stress
        if 'cpu' in active_tests:
            processes = active_tests['cpu'].get('processes', [])
            for p in processes:
                if p.is_alive():
                    p.terminate()
    
    sys.exit(0)


if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGTERM, cleanup_on_exit)
    signal.signal(signal.SIGINT, cleanup_on_exit)
    
    logger.info("Starting HemoStat Test API on port 5000...")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
