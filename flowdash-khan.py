import json
import time
import os
import os.path
from glob import glob

import requests
from requests.auth import HTTPBasicAuth

from dotenv import load_dotenv
load_dotenv()


auth = HTTPBasicAuth(os.environ['FLOWDASH_USER'], os.environ['FLOWDASH_API_PASS'])

def get_masterypoints() -> int:
    "Get the mastery points from khan academy using selenium"

    from selenium import webdriver
    from selenium.common.exceptions import NoSuchElementException

    url = 'https://www.khanacademy.org/math/multivariable-calculus'
    selector = '[data-test-id="subject-points-earned-label"]'

    firefox_profile_path = glob(os.path.join(os.environ['HOME'], '.mozilla/firefox/*.default-release'))[0]
    print('Loading profile from ' + firefox_profile_path)
    fp = webdriver.FirefoxProfile(firefox_profile_path)
    print('Launching Firefox webdriver with profile')
    driver = webdriver.Firefox(fp)

    print('Navigating to ' + url)
    driver.get(url)

    print('Waiting for mastery points to appear')
    mastery_points_text = ''
    while mastery_points_text.strip() == '':
        try:
            elem = driver.find_element_by_css_selector(selector)
            mastery_points_text = elem.text
        except NoSuchElementException:
            # must not have loaded yet
            pass
        time.sleep(0.1)

    driver.close()

    mastery_points = mastery_points_text.split(' ')[0]
    return int(mastery_points)


def track_masterypoints(mastery_points: int):
    "Send the mastery points to flowdash"

    url = 'https://flowdash.co/api/tracking'

    resp = requests.post(url, auth=auth, data={
        "date": time.strftime('%Y-%m-%d'),
        "data": json.dumps({
            "masterypoints": mastery_points,
        }),
    })

    print(resp)
    print(resp.text)


def main():
    "Log mastery points to flowdash"
    # very slow, starting firefox takes a long time
    mastery_points = get_masterypoints()
    track_masterypoints(mastery_points)

if __name__ == '__main__':
    main()
