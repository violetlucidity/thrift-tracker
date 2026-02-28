from .vinted import VintedScraper
from .depop import DepopScraper
from .ebay import EbayScraper
from .poshmark import PoshmarkScraper

SCRAPERS = {
    "vinted": VintedScraper,
    "depop": DepopScraper,
    "ebay": EbayScraper,
    "poshmark": PoshmarkScraper,
}
