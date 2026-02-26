from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from thrift_tracker import runner

_scheduler = None


def start_scheduler(config: dict):
    """Start the background scheduler for automatic scrape runs."""
    global _scheduler

    schedule = config.get("schedule", {})
    days = schedule.get("days_of_week", ["tue", "fri"])
    hour = schedule.get("hour", 8)
    minute = schedule.get("minute", 0)

    day_of_week = ",".join(days)

    _scheduler = BackgroundScheduler()
    trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute, timezone="UTC")
    _scheduler.add_job(runner.run_scrape, trigger, args=[config], id="scrape_job")
    _scheduler.start()

    hhmm = f"{hour:02d}:{minute:02d}"
    print(f"[scheduler] Scrape scheduled: {', '.join(days)} at {hhmm} UTC")

    try:
        return _scheduler
    except KeyboardInterrupt:
        _scheduler.shutdown()
