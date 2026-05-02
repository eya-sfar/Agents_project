"""
run_agents.py
Entry point for the MAS pipeline.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USAGE EXAMPLES (no researcher names needed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# By country (finds top researchers in Tunisia automatically)
python run_agents.py --country TN

# By institution name (fully automatic)
python run_agents.py --institution "Universite de Tunis El Manar"

# By research topic
python run_agents.py --topic "machine learning"
python run_agents.py --topic "bioinformatics"
python run_agents.py --topic "NLP Arabic"

# Combine filters
python run_agents.py --country TN --topic "deep learning" --max-authors 100

# Re-run only analysis (no scraping) — useful after manual DB edits
python run_agents.py --skip-scrape --n-clusters 6

# Run on a schedule (every hour)
python run_agents.py --country TN --schedule --interval 3600

# Scrape a university website for lab names
python run_agents.py --university-url "https://www.fst.utm.tn/laboratoires" --country TN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import sys
import time
import argparse
import schedule

from database.connection import init_db
from agents import AgentCoordinator
from config.settings import settings
from utils.logger import logger


def run_once(args):
    coordinator = AgentCoordinator()
    coordinator.start(
        country_code=args.country or None,
        institution_name=args.institution or None,
        topic=args.topic or None,
        seed_researchers=[n.strip() for n in (args.researchers or "").split(",") if n.strip()],
        university_url=args.university_url or None,
        skip_scrape=args.skip_scrape,
        n_clusters=args.n_clusters,
        max_authors=args.max_authors,
    )


def main():
    parser = argparse.ArgumentParser(
        description="University Observatory — MAS Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Discovery options
    disc = parser.add_argument_group("Discovery (pick at least one)")
    disc.add_argument("--country",        type=str, default="", metavar="CODE",
                      help='ISO country code, e.g. "TN", "FR", "DZ"')
    disc.add_argument("--institution",    type=str, default="", metavar="NAME",
                      help='Institution name, e.g. "Universite de Tunis El Manar"')
    disc.add_argument("--topic",          type=str, default="", metavar="KEYWORD",
                      help='Research topic, e.g. "machine learning"')
    disc.add_argument("--university-url", type=str, default="", metavar="URL",
                      help="University website URL to scrape for lab names")
    disc.add_argument("--researchers",    type=str, default="", metavar="NAMES",
                      help="Optional comma-separated fallback names")

    # Pipeline options
    pipe = parser.add_argument_group("Pipeline options")
    pipe.add_argument("--skip-scrape",  action="store_true",
                      help="Skip data collection, re-run analysis only")
    pipe.add_argument("--n-clusters",   type=int, default=settings.agents.CLUSTERING_N_CLUSTERS,
                      help=f"Number of clusters (default: {settings.agents.CLUSTERING_N_CLUSTERS})")
    pipe.add_argument("--max-authors",  type=int, default=settings.agents.MAX_RESEARCHERS,
                      help=f"Max researchers to import (default: {settings.agents.MAX_RESEARCHERS})")

    # Schedule options
    sched = parser.add_argument_group("Schedule")
    sched.add_argument("--schedule",  action="store_true", help="Run repeatedly on a schedule")
    sched.add_argument("--interval",  type=int, default=settings.agents.SCRAPE_INTERVAL,
                       help="Schedule interval in seconds (default: 3600)")

    args = parser.parse_args()

    # Validate: at least one discovery option unless skip_scrape
    if not args.skip_scrape and not any([args.country, args.institution, args.topic, args.researchers]):
        parser.print_help()
        print("\n⚠️  Please provide at least one discovery option (--country, --institution, --topic).")
        print("   Or use --skip-scrape to re-run analysis on existing data.")
        print("\n   Quick start:  python run_agents.py --country TN")
        sys.exit(1)

    logger.info("Initialising database ...")
    init_db()

    if args.schedule:
        logger.info(f"Scheduled mode — interval: {args.interval}s")
        schedule.every(args.interval).seconds.do(run_once, args=args)
        run_once(args)
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        run_once(args)


if __name__ == "__main__":
    main()
