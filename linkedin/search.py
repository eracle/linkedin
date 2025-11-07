
import logging
import random
from time import sleep
from urllib.parse import urlencode, urlparse

from linkedin_api import Linkedin
from linkedin_api.client import Client
from linkedin_api.utils.helpers import get_id_from_urn

from linkedin.login import build_playwright

logger = logging.getLogger(__name__)


class CustomClient(Client):
    def _set_session_cookies(self, cookies):
        """
        Set cookies of the current session and save them to a file named as the username.
        """
        for cookie in cookies:
            self.session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie["domain"],
                path=cookie["path"],
            )
        self.session.headers["csrf-token"] = self.session.cookies["JSESSIONID"].strip(
            '"'
        )


def my_default_evade():
    """
    A catch-all method to try and evade suspension from Linkedin.
    Currenly, just delays the request by a random (bounded) time
    """
    sleep(
        random.uniform(0.2, 0.7)
    )  # sleep a random duration to try and evade suspention


class CustomLinkedin(Linkedin):
    def __init__(
        self,
        username,
        password,
        *,
        authenticate=True,
        refresh_cookies=False,
        debug=False,
        proxies={},
        cookies=None,
        cookies_dir=None,
    ):
        """Constructor method"""
        self.client = CustomClient(
            refresh_cookies=refresh_cookies,
            debug=debug,
            proxies=proxies,
            cookies_dir=cookies_dir,
        )
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logger

        if authenticate:
            if cookies:
                # If the cookies are expired, the API won't work anymore since
                # `username` and `password` are not used at all in this case.
                self.client._set_session_cookies(cookies)
            else:
                self.client.authenticate(username, password)

    def _fetch(self, uri, evade=my_default_evade, **kwargs):
        """
        GET request to Linkedin API
        """
        return super()._fetch(uri, evade, **kwargs)

    def _post(self, uri, evade=my_default_evade, **kwargs):
        """
        POST request to Linkedin API
        """
        return super()._post(uri, evade, **kwargs)

    def get_profile(self, public_id=None, urn_id=None, with_skills=True):
        """
        Return data for a single profile.

        [public_id] - public identifier i.e. tom-quirk-1928345
        [urn_id] - id provided by the related URN
        """
        # NOTE this still works for now, but will probably eventually have to be converted to
        # https://www.linkedin.com/voyager/api/identity/profiles/ACoAAAKT9JQBsH7LwKaE9Myay9WcX8OVGuDq9Uw
        res = self._fetch(f"/identity/profiles/{public_id or urn_id}/profileView")

        data = res.json()
        if data and "status" in data and data["status"] != 200:
            self.logger.info(f"request failed: {data}")
            return {}

        # massage [profile] data
        profile = data["profile"]
        if "miniProfile" in profile:
            if "picture" in profile["miniProfile"]:
                profile["displayPictureUrl"] = profile["miniProfile"]["picture"][
                    "com.linkedin.common.VectorImage"
                ]["rootUrl"]
            profile["profile_id"] = get_id_from_urn(profile["miniProfile"]["entityUrn"])

            del profile["miniProfile"]

        del profile["defaultLocale"]
        del profile["supportedLocales"]
        del profile["versionTag"]
        del profile["showEducationOnProfileTopCard"]

        # massage [experience] data
        experience = data["positionView"]["elements"]
        for item in experience:
            if "company" in item and "miniCompany" in item["company"]:
                if "logo" in item["company"]["miniCompany"]:
                    logo = item["company"]["miniCompany"]["logo"].get(
                        "com.linkedin.common.VectorImage"
                    )
                    if logo:
                        item["companyLogoUrl"] = logo["rootUrl"]
                del item["company"]["miniCompany"]

        profile["experience"] = experience

        # massage [skills] data
        # skills = [item["name"] for item in data["skillView"]["elements"]]
        # profile["skills"] = skills

        profile["skills"] = self.get_profile_skills(public_id=public_id, urn_id=urn_id)

        # massage [education] data
        education = data["educationView"]["elements"]
        for item in education:
            if "school" in item:
                if "logo" in item["school"]:
                    item["school"]["logoUrl"] = item["school"]["logo"][
                        "com.linkedin.common.VectorImage"
                    ]["rootUrl"]
                    del item["school"]["logo"]

        profile["education"] = education

        # language
        profile["locale"] = data["primaryLocale"]["language"]
        return profile


def extract_profile_from_url(url, cookies):
    logger.debug(f"extract_profile_id_from_url: {url}")
    api_client = CustomLinkedin(
        username=None, password=None, authenticate=True, cookies=cookies, debug=True
    )

    # Parse the URL
    parsed_url = urlparse(url)

    # Split the path and get the second part
    profile_id = parsed_url.path.split("/")[2]

    logger.debug(f"profile_id: {profile_id}")
    return extract_profile_info(api_client, profile_id)


def filter_istruction_dict(elem):
    wanted_istr = {
        "schoolName",
        "degreeName",
        "fieldOfStudy",
        "timePeriod",
        # 'description',
        "grade",
    }
    return dict([(k, v) for k, v in elem.items() if k in wanted_istr])


def filter_experience_dict(elem):
    wanted_experience = {
        "companyName",
        "industries",
        "title",
        "startDate",
        "timePeriod",
        "geoLocationName",
        "description",
        "locationName",
        "company",
    }
    return dict([(k, v) for k, v in elem.items() if k in wanted_experience])


def filter_fields(contact_profile):
    allowed_fields = [
        "linkedinUrl",
        "firstName",
        "lastName",
        "headline",
        "summary",
        "industryName",
        "geoCountryName",
        "geoCountryUrn",
        "publicIdentifier",
        "connection_msg",
        "email_address",
        "phone_numbers",
        "education",
        "experience",
        "skills",
        "locale",
    ]

    # Filter out the fields using dictionary comprehension
    filtered_dict = {k: v for k, v in contact_profile.items() if k in allowed_fields}

    return filtered_dict


def extract_profile_info(api_client, contact_public_id):
    """
    Extracts profile information for a given LinkedIn user.

    Args:
        api_client: The API client instance.
        contact_public_id: The public ID of the LinkedIn user.

    Returns:
        A dictionary containing the user's profile information.
    """
    contact_profile = api_client.get_profile(contact_public_id)
    contact_info = api_client.get_profile_contact_info(contact_public_id)

    email_address = contact_info.get("email_address")
    phone_numbers = contact_info.get("phone_numbers")

    education = list(map(filter_istruction_dict, contact_profile.pop("education", [])))
    experience = list(
        map(filter_experience_dict, contact_profile.pop("experience", []))
    )

    return dict(
        email_address=email_address,
        phone_numbers=phone_numbers,
        education=education,
        experience=experience,
        **filter_fields(contact_profile),
    )


BASE_SEARCH_URL = "https://www.linkedin.com/search/results/people/"


def search(keyword: str, max_results: int = 10):
    """
    Searches for people on LinkedIn by keyword.
    """
    page, context, browser, playwright = build_playwright(login=True)

    params = {
        "keywords": keyword,
        "origin": "GLOBAL_SEARCH_HEADER",
    }
    search_url = BASE_SEARCH_URL + "?" + urlencode(params)

    logger.info(f"Navigating to search URL: {search_url}")
    page.goto(search_url)

    results = []
    result_container_xpath = "//li[contains(@class, 'reusable-search__result-container')]"

    # Wait for the search results to load
    page.wait_for_selector(f"xpath={result_container_xpath}", timeout=15000)

    # Get all result containers
    result_locators = page.locator(f"xpath={result_container_xpath}").all()

    logger.info(f"Found {len(result_locators)} search results on the first page.")

    for i, result_locator in enumerate(result_locators):
        if i >= max_results:
            break

        profile_link_locator = result_locator.locator(
            "xpath=.//a[contains(@href, '/in/') and not(contains(@href, '/sales/lead/'))]"
        )
        if profile_link_locator.count() > 0:
            profile_url = profile_link_locator.first.get_attribute("href")
            if profile_url:
                name_locator = result_locator.locator(
                    "xpath=.//span[@aria-hidden='true']"
                ).first
                headline_locator = result_locator.locator(
                    "xpath=.//div[contains(@class, 'entity-result__primary-subtitle')]"
                ).first

                name = name_locator.inner_text() if name_locator else ""
                headline = headline_locator.inner_text() if headline_locator else ""

                results.append(
                    {
                        "profile_url": profile_url,
                        "name": name,
                        "headline": headline,
                    }
                )

    # Enrich profiles with API data
    if results:
        cookies = context.cookies()
        api = CustomLinkedin(
            username=None, password=None, authenticate=True, cookies=cookies, debug=True
        )
        enriched_results = []
        for profile in results:
            try:
                profile_id = urlparse(profile["profile_url"]).path.split("/")[2]
                profile_data = extract_profile_info(api, profile_id)
                enriched_results.append(profile_data)
            except Exception as e:
                logger.error(f"Could not enrich profile {profile['profile_url']}: {e}")
                enriched_results.append(profile) # append basic info if enrichment fails

        results = enriched_results


    # Clean up
    context.close()
    browser.close()
    playwright.stop()

    return results
