# linkedin/sessions/account.py
from __future__ import annotations

import logging
from linkedin.navigation.utils import human_delay
from linkedin.navigation.throttle import get_smooth_scrape_count, _wait_counter

from linkedin.conf import get_account_config
from linkedin.navigation.login import init_playwright_session

logger = logging.getLogger(__name__)


class AccountSession:
    def __init__(self, key: "SessionKey"):
        from linkedin.db.engine import Database
        self.key = key
        self.handle = key.handle
        self.campaign_name = key.campaign_name
        self.csv_hash = key.csv_hash

        self.account_cfg = get_account_config(self.handle)
        self.db = Database.from_handle(self.handle)

        # Playwright objects – created on first access or after crash
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

    def ensure_browser(self):
        """Launch or recover browser + login if needed. Call before using .page"""
        if not self.page or self.page.is_closed():
            logger.info("Launching/recovering browser for %s – %s", self.handle, self.campaign_name)
            self.page, self.context, self.browser, self.playwright = init_playwright_session(
                session=self,
                handle=self.handle
            )

    def wait(self):
        """Human-like pause + load wait + logging of pending scrapes"""
        human_delay()
        self.page.wait_for_load_state("load")

        from linkedin.db.engine import count_pending_scrape
        pending = count_pending_scrape(self)

        logger.debug(f"****************************************")
        logger.debug(f"Wait #{_wait_counter:04d} | Profiles still needing scrape: {pending}")
        logger.debug(f"****************************************")

        _ = get_smooth_scrape_count(pending)


    def close(self):
        if self.context:
            try:
                self.context.close()
                if self.browser:
                    self.browser.close()
                if self.playwright:
                    self.playwright.stop()
                logger.info("Browser closed gracefully (%s)", self.handle)
            except Exception as e:
                logger.debug("Error closing browser: %s", e)
            finally:
                self.page = self.context = self.browser = self.playwright = None

        self.db.close()
        logger.info("Account session closed → %s", self.key)

    def __del__(self):
        try:
            self.close()
        except:
            pass

    def __repr__(self) -> str:
        return f"<AccountSession {self.key}>"
