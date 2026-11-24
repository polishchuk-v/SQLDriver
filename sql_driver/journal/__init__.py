"""Журналювання запитів у службовій БД."""

from .logger import JournalSession, QueryLogger

__all__ = ["JournalSession", "QueryLogger"]
