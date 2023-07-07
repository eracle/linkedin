import logging
import random
from time import sleep

from linkedin_api import Linkedin
from linkedin_api.client import Client
from linkedin_api.utils.helpers import get_id_from_urn

logger = logging.getLogger(__name__)


def my_default_evade():
    """
    A catch-all method to try and evade suspension from Linkedin.
    Currenly, just delays the request by a random (bounded) time
    """
    sleep(random.uniform(0.2, 0.7))  # sleep a random duration to try and evade suspention


class CustomClient(Client):
    def _set_session_cookies(self, cookies):
        """
        Set cookies of the current session and save them to a file named as the username.
        """
        for cookie in cookies:
            self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'])
        self.session.headers["csrf-token"] = self.session.cookies["JSESSIONID"].strip(
            '"'
        )


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

        return profile
