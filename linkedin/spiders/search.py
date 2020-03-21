import time

from scrapy import Spider
from scrapy import Request

from linkedin.spiders.selenium import get_by_xpath_or_none, SeleniumSpiderMixin

"""
Number of seconds to wait checking if the page is a "No Result" type.
"""
NO_RESULT_WAIT_TIMEOUT = 3


class SearchSpider(SeleniumSpiderMixin, Spider):
    """
    Abstract class for for generic search on linkedin.
    """

    def parser_search_results_page(self, response):
        print('Now parsing search result page')

        no_result_found_xpath = '//*[text()="No results found."]'

        no_result_response = get_by_xpath_or_none(driver=self.driver,
                                                  xpath=no_result_found_xpath,
                                                  wait_timeout=NO_RESULT_WAIT_TIMEOUT,
                                                  logs=False)

        if no_result_response is not None:
            print('"No results" message shown, stop crawling this company')
            return
        else:
            # company extraction temporary disabled
            # company = extract_company(self.driver)
            # print(f'Company:{company}')

            users = extracts_linkedin_users(self.driver,
                                            #company=company,
                                            api_client=self.api_client)
            for user in users:
                yield user


            # incrementing the index at the end of the url
            url = response.request.url
            next_url_split = url.split('=')
            index = int(next_url_split[-1])
            next_url = '='.join(next_url_split[:-1]) + '=' + str(index + 1)

            max_page = response.meta.get('max_page', None)
            if max_page is not None:
                if index >= max_page:
                    return

            yield Request(url=next_url,
                          callback=self.parser_search_results_page,
                          meta={'max_page': max_page},
                          dont_filter=True,
                          )
    
######################
# Module's functions:
######################
def extracts_linkedin_users(driver, api_client, company=None):
    """
    Gets from a page containing a list of users, all the users.
    For instance: https://www.linkedin.com/search/results/people/?facetCurrentCompany=[%22221027%22]
    :param driver: The webdriver, logged in, and located in the page which lists users.
    :return: Iterator on LinkedinUser.
    """

    for i in range(1, 11):
        print(f'loading {i}th user')

        last_result_xpath = f'//li[{i}]/*/div[@class="search-result__wrapper"]'

        result = get_by_xpath_or_none(driver, last_result_xpath)
        if result is not None:
            link_elem = get_by_xpath_or_none(result, './/*[@class="search-result__result-link ember-view"]')
            link = link_elem.get_attribute('href') if link_elem is not None else None

            name_elem = get_by_xpath_or_none(result, './/*[@class="name actor-name"]')
            name = name_elem.text if name_elem is not None else None

            title_elem = get_by_xpath_or_none(result, './/p')
            title = title_elem.text if name_elem is not None else None

            # extract_profile_id_from_url
            profile_id = link.split('/')[-2]
            user = extract_contact_info(api_client, profile_id)

            yield user

            if link_elem is not None:
                driver.execute_script("arguments[0].scrollIntoView();", link_elem)
            elif name_elem is not None:
                driver.execute_script("arguments[0].scrollIntoView();", name_elem)
            elif title_elem is not None:
                driver.execute_script("arguments[0].scrollIntoView();", title_elem)
            else:
                print("Was not possible to scroll")

        time.sleep(0.7)


def extract_contact_info(api_client, contact_public_id):
    contact_profile = api_client.get_profile(contact_public_id)
    contact_info = api_client.get_profile_contact_info(contact_public_id)

    lastName = contact_profile['lastName']
    firstName = contact_profile['firstName']

    email_address = contact_info['email_address']
    phone_numbers = contact_info['phone_numbers']

    education = contact_profile['education']
    experience = contact_profile['experience']

    current_work = [exp for exp in experience if exp.get('timePeriod', {}).get('endDate') is None]

    return dict(lastName=lastName,
                firstName=firstName,
                email_address=email_address,
                phone_numbers=phone_numbers,
                education=education,
                experience=experience,
                current_work=current_work,
                )

