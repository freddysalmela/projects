"""Shared state flags accessible across all modules without circular imports."""
import threading

stop_event = threading.Event()
