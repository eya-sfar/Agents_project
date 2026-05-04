"""
run_agents.py
Point d'entrée principal — utilise le modèle Mesa ObservatoryModel.

EXEMPLES :
  python run_agents.py --country TN
  python run_agents.py --country FR --max-authors 100
  python run_agents.py --institution "Universite de Tunis El Manar"
  python run_agents.py --topic "machine learning"
  python run_agents.py --skip-scrape --n-clusters 6
  python run_agents.py --country TN --schedule --interval 3600
"""
import sys, time, argparse, schedule

from database.connection import init_db
from agents.mas_model import ObservatoryModel
from config.settings import settings
from utils.logger import logger


def run_once(args):
    model = ObservatoryModel(
        country_code     = args.country     or None,
        institution_name = args.institution or None,
        topic            = args.topic       or None,
        seed_researchers = [n.strip() for n in (args.researchers or "").split(",") if n.strip()],
        skip_scrape      = args.skip_scrape,
        n_clusters       = args.n_clusters,
        max_authors      = args.max_authors,
        max_pages        = args.max_pages,
    )
    report = model.run_pipeline()
    logger.info(f"Pipeline report: {report}")


def main():
    parser = argparse.ArgumentParser(
        description="University Observatory — MAS Runner (Mesa)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    disc = parser.add_argument_group("Découverte (au moins un requis)")
    disc.add_argument("--country",      type=str, default="", metavar="CODE",
                      help='Code ISO ou nom complet : "TN", "FR", "Tunisia"')
    disc.add_argument("--institution",  type=str, default="", metavar="NAME",
                      help='"Universite de Tunis El Manar"')
    disc.add_argument("--topic",        type=str, default="", metavar="KW",
                      help='"machine learning", "NLP Arabic"')
    disc.add_argument("--researchers",  type=str, default="", metavar="NAMES",
                      help="Noms séparés par virgule (fallback)")

    pipe = parser.add_argument_group("Pipeline")
    pipe.add_argument("--skip-scrape",  action="store_true",
                      help="Saute la collecte, relance seulement l'analyse")
    pipe.add_argument("--n-clusters",   type=int,
                      default=settings.agents.CLUSTERING_N_CLUSTERS)
    pipe.add_argument("--max-authors",  type=int,
                      default=settings.agents.MAX_RESEARCHERS)
    pipe.add_argument("--max-pages",    type=int, default=5,
                      help="Pages OpenAlex par agent (25 résultats/page)")

    sched = parser.add_argument_group("Schedule")
    sched.add_argument("--schedule",  action="store_true")
    sched.add_argument("--interval",  type=int,
                       default=settings.agents.SCRAPE_INTERVAL)

    args = parser.parse_args()

    if not args.skip_scrape and not any([args.country, args.institution, args.topic, args.researchers]):
        parser.print_help()
        print("\n⚠️  Donne au moins une option de découverte :")
        print("   python run_agents.py --country TN")
        print("   python run_agents.py --institution \"Universite de Tunis El Manar\"")
        print("   python run_agents.py --topic \"machine learning\"")
        sys.exit(1)

    logger.info("Initialisation de la base de données …")
    init_db()

    if args.schedule:
        logger.info(f"Mode schedulé — intervalle: {args.interval}s")
        schedule.every(args.interval).seconds.do(run_once, args=args)
        run_once(args)
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        run_once(args)


if __name__ == "__main__":
    main()
