import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import threading
from app.scraper.chrome_session import ChromeSession
from app.scraper.dapachecker import scrape_moz
from app.scraper.ahrefs import scrape_ahrefs
from app.utils.constants import HEADLESS


def main():
    domain = sys.argv[1] if len(sys.argv) > 1 else "google.com"
    print(f"\nCek domain: {domain}\n")

    moz = {}
    ahref = {}

    def run_moz():
        with ChromeSession(headless=HEADLESS) as driver:
            moz.update(scrape_moz(driver, domain))

    def run_ahrefs():
        with ChromeSession(headless=HEADLESS) as driver:
            ahref.update(scrape_ahrefs(driver, domain))

    t1 = threading.Thread(target=run_moz)
    t2 = threading.Thread(target=run_ahrefs)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print("\n--- DA/PA/SS/Age ---")
    print(f"  DA  : {moz.get('da')}")
    print(f"  PA  : {moz.get('pa')}")
    print(f"  SS  : {moz.get('ss')}")
    print(f"  Age : {moz.get('age')}")

    print("\n--- DR/BC/RD (Ahrefs) ---")
    print(f"  DR     : {ahref.get('dr')}")
    print(f"  BC     : {ahref.get('bc')} ({ahref.get('bc_df')}% dofollow)")
    print(f"  RD     : {ahref.get('rd')} ({ahref.get('rd_df')}% dofollow)")
    backlinks = ahref.get("backlinks", [])
    if backlinks:
        print(f"\n  Backlinks sample ({len(backlinks)} baris):")
        for bl in backlinks[:5]:
            print(f"    DR {bl['dr']} — {bl['ref_title']}")


if __name__ == "__main__":
    main()
